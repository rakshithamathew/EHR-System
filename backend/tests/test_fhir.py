import asyncio

import httpx
import pytest

from app.ehr import epic, hapi, oracle
from app.routes import normalize_condition, normalize_medication, normalize_patient


def test_fhir_pagination_follows_next_links() -> None:
    requests: list[httpx.Request] = []
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = ({"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": "1"}}], "link": [{"relation": "next", "url": "https://example.test/Patient?page=2"}]} if len(requests) == 1 else {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": "2"}}]})
        return httpx.Response(200, json=payload, request=request)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await hapi.FHIRClient("https://example.test", client=client).all("Patient", {"_count": 5})
    assert [item["id"] for item in asyncio.run(run())] == ["1", "2"]
    assert len(requests) == 2


def test_rate_limit_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    monkeypatch.setattr(hapi, "_retry_wait", lambda *_: 0)
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429 if attempts == 1 else 200, json={"resourceType": "Bundle"}, request=request)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await hapi.FHIRClient("https://example.test", client=client).all("Patient")
    assert asyncio.run(run()) == []
    assert attempts == 2


def test_oracle_sync_uses_search_and_pagination() -> None:
    requests: list[httpx.Request] = []
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = {"resourceType": "Bundle", "entry": [], "link": [{"relation": "next", "url": "https://oracle.test/Patient?page=2"}]} if len(requests) == 1 else {"resourceType": "Bundle", "entry": []}
        return httpx.Response(200, json=payload, request=request)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await oracle.fetch_patients(hapi.FHIRClient("https://oracle.test", client=client))
    asyncio.run(run())
    assert requests[0].url.params["name"] == "smart"
    assert len(requests) == 2


def test_epic_pkce_state_is_single_use() -> None:
    state, challenge = epic.begin_authorization()
    assert state and challenge
    pending = epic.consume_authorization(state)
    assert pending and pending.verifier
    assert epic.consume_authorization(state) is None


def test_normalizers_extract_dashboard_fields() -> None:
    patient = normalize_patient({"id": "p1", "name": [{"given": ["Ada"], "family": "Lovelace"}], "birthDate": "1815-12-10"})
    condition = normalize_condition({"id": "c1", "clinicalStatus": {"coding": [{"code": "active"}]}, "code": {"coding": [{"code": "x", "display": "Example"}]}})
    medication = normalize_medication({"id": "m1", "status": "active", "medicationCodeableConcept": {"coding": [{"code": "rx", "display": "Medicine"}]}})
    assert patient["name"] == "Ada Lovelace"
    assert condition["clinical_status"] == "active"
    assert medication["medication_display"] == "Medicine"
