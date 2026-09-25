import asyncio
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import httpx

from app.connectors.base import FHIRConnector
from app.connectors.epic import EpicFHIRConnector
from app.connectors.hapi import HAPIConnector
from app.connectors.oracle import OracleConnector
from app.api.epic import EPIC_FHIR_AUDIENCE, EPIC_SCOPES, epic_login
from app.core.config import settings
from app.services.epic_auth_service import EpicOAuthStore
from app.utils.fhir import (
    FHIRPage,
    FHIRQueryParams,
    FHIRResource,
    paginate_fhir_bundle,
)


class StubConnector(FHIRConnector):
    async def get_patient(self, patient_external_id: str) -> FHIRResource:
        return {}

    async def get_patient_page(
        self,
        *,
        page: int,
        count: int,
        search: str | None = None,
    ) -> FHIRPage:
        return {"resources": [], "has_next": False}

    async def get_patients(self) -> list[FHIRResource]:
        return []

    async def get_conditions(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        return []

    async def get_medications(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        return []


def test_pagination_collects_resources_from_next_bundle_page() -> None:
    first_url = "https://fhir.example/Patient?_count=1"
    second_url = "https://fhir.example/Patient?page=2"
    pages: dict[str, FHIRResource] = {
        first_url: {
            "resourceType": "Bundle",
            "entry": [{"resource": {"resourceType": "Patient", "id": "1"}}],
            "link": [{"relation": "next", "url": second_url}],
        },
        second_url: {
            "resourceType": "Bundle",
            "entry": [{"resource": {"resourceType": "Patient", "id": "2"}}],
        },
    }
    requests: list[tuple[str, FHIRQueryParams | None]] = []

    async def fetch_page(
        url: str,
        params: FHIRQueryParams | None,
    ) -> FHIRResource:
        requests.append((url, params))
        return pages[url]

    resources = asyncio.run(
        paginate_fhir_bundle(
            first_url,
            fetch_page,
            params={"_count": 1},
        )
    )

    assert [resource["id"] for resource in resources] == ["1", "2"]
    assert requests == [
        (first_url, {"_count": 1}),
        (second_url, None),
    ]


def test_get_retries_after_rate_limit_response() -> None:
    attempts = 0

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                request=request,
            )

        return httpx.Response(
            200,
            json={"resourceType": "Bundle", "entry": []},
            request=request,
        )

    async def make_request() -> FHIRResource:
        transport = httpx.MockTransport(handle_request)
        async with httpx.AsyncClient(transport=transport) as client:
            connector = StubConnector(
                "https://fhir.example",
                client=client,
            )
            return await connector._get("Patient")

    response = asyncio.run(make_request())

    assert response == {"resourceType": "Bundle", "entry": []}
    assert attempts == 2


def test_hapi_can_fetch_a_configured_patient_directly() -> None:
    requested_urls: list[str] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "resourceType": "Patient",
                "id": "4237",
                "name": [{"text": "Ravi Vangapandu"}],
            },
            request=request,
        )

    async def fetch_patient() -> FHIRResource:
        transport = httpx.MockTransport(handle_request)
        async with httpx.AsyncClient(transport=transport) as client:
            connector = HAPIConnector(
                base_url="https://hapi.fhir.org/baseR4",
                client=client,
            )
            return await connector.get_patient("4237")

    patients = asyncio.run(fetch_patient())

    assert patients["id"] == "4237"
    assert requested_urls == ["https://hapi.fhir.org/baseR4/Patient/4237"]


def test_hapi_patient_page_follows_server_next_link() -> None:
    requests_seen: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        if len(requests_seen) == 1:
            payload = {
                "resourceType": "Bundle",
                "entry": [{"resource": {"resourceType": "Patient", "id": "1"}}],
                "link": [
                    {
                        "relation": "next",
                        "url": "https://hapi.fhir.org/baseR4/Patient?cursor=next",
                    }
                ],
            }
        else:
            payload = {
                "resourceType": "Bundle",
                "entry": [{"resource": {"resourceType": "Patient", "id": "2"}}],
            }
        return httpx.Response(200, json=payload, request=request)

    async def search() -> FHIRPage:
        transport = httpx.MockTransport(handle_request)
        async with httpx.AsyncClient(transport=transport) as client:
            connector = HAPIConnector(
                base_url="https://hapi.fhir.org/baseR4",
                client=client,
            )
            return await connector.get_patient_page(page=2, count=5)

    patients = asyncio.run(search())

    assert patients == {
        "resources": [{"resourceType": "Patient", "id": "2"}],
        "has_next": False,
    }
    assert requests_seen[0].url.params.get("_count") == "5"
    assert str(requests_seen[1].url) == (
        "https://hapi.fhir.org/baseR4/Patient?cursor=next"
    )
    assert requests_seen[0].headers["Accept"] == "application/fhir+json"


def test_oracle_patient_page_uses_public_sandbox_base_url() -> None:
    requests_seen: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return httpx.Response(
            200,
            json={"resourceType": "Bundle", "entry": []},
            request=request,
        )

    async def search() -> FHIRPage:
        transport = httpx.MockTransport(handle_request)
        async with httpx.AsyncClient(transport=transport) as client:
            connector = OracleConnector(
                base_url=(
                    "https://fhir-open.cerner.com/r4/"
                    "ec2458f2-1e24-41c8-b71b-0e701af7583d"
                ),
                client=client,
            )
            return await connector.get_patient_page(page=1, count=20)

    result = asyncio.run(search())

    assert result == {"resources": [], "has_next": False}
    assert requests_seen[0].url.params.get("_count") == "20"
    assert requests_seen[0].url.params.get("name") == "smart"
    assert requests_seen[0].headers["Accept"] == "application/fhir+json"


def test_epic_pkce_uses_s256_and_state_is_single_use() -> None:
    store = EpicOAuthStore()

    state, session_id, verifier, challenge = store.begin_authorization()
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")

    assert state
    assert session_id
    assert challenge == expected_challenge
    pending = store.consume_authorization(state)
    assert pending is not None
    assert pending.session_id == session_id
    assert pending.code_verifier == verifier
    assert store.consume_authorization(state) is None


def test_epic_patient_page_sends_bearer_token() -> None:
    requests_seen: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return httpx.Response(
            200,
            json={
                "resourceType": "Bundle",
                "entry": [
                    {"resource": {"resourceType": "Patient", "id": "epic-1"}}
                ],
            },
            request=request,
        )

    async def search() -> FHIRPage:
        transport = httpx.MockTransport(handle_request)
        async with httpx.AsyncClient(transport=transport) as client:
            connector = EpicFHIRConnector(
                base_url="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
                access_token="sandbox-token",
                client=client,
            )
            return await connector.get_patient_page(page=1, count=20)

    result = asyncio.run(search())

    assert result["resources"][0]["id"] == "epic-1"
    assert requests_seen[0].headers["Authorization"] == "Bearer sandbox-token"
    assert requests_seen[0].headers["Accept"] == "application/fhir+json"


def test_epic_login_redirect_contains_required_smart_parameters(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "epic_authorization_url",
        "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize",
    )
    monkeypatch.setattr(
        settings,
        "epic_fhir_base_url",
        EPIC_FHIR_AUDIENCE,
    )
    monkeypatch.setattr(
        settings,
        "epic_client_id",
        "6b14ff08-2522-41fa-9c83-0b395a36add4",
    )
    monkeypatch.setattr(
        settings,
        "epic_redirect_uri",
        "http://localhost:5173/callback",
    )

    response = asyncio.run(epic_login())
    redirect = urlparse(response.headers["location"])
    query = parse_qs(redirect.query)

    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["6b14ff08-2522-41fa-9c83-0b395a36add4"]
    assert query["redirect_uri"] == ["http://localhost:5173/callback"]
    assert query["scope"] == [EPIC_SCOPES]
    assert query["aud"] == [EPIC_FHIR_AUDIENCE]
    assert query["state"][0]
    assert query["code_challenge"][0]
    assert query["code_challenge_method"] == ["S256"]
