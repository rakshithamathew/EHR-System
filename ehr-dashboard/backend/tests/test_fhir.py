import asyncio

import httpx

from app.connectors.base import FHIRConnector
from app.connectors.hapi import HAPIConnector
from app.utils.fhir import FHIRQueryParams, FHIRResource, paginate_fhir_bundle


class StubConnector(FHIRConnector):
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

    async def fetch_patient() -> list[FHIRResource]:
        transport = httpx.MockTransport(handle_request)
        async with httpx.AsyncClient(transport=transport) as client:
            connector = HAPIConnector(
                base_url="https://hapi.fhir.org/baseR4",
                patient_id="4237",
                client=client,
            )
            return await connector.get_patients()

    patients = asyncio.run(fetch_patient())

    assert patients[0]["id"] == "4237"
    assert requested_urls == ["https://hapi.fhir.org/baseR4/Patient/4237"]
