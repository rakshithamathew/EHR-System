import asyncio
from collections import deque
from collections.abc import Mapping
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urljoin

import httpx

FHIRResource = dict[str, Any]
RETRYABLE = {429, 500, 502, 503, 504}


class FHIRClient:
    """Small shared HTTP client with FHIR pagination, retry, and rate limiting."""

    def __init__(self, base_url: str, token: str | None = None, client: httpx.AsyncClient | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Accept": "application/fhir+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(15, connect=5))
        self.owns_client = client is None
        self.timestamps: deque[float] = deque()
        self.lock = asyncio.Lock()

    async def close(self) -> None:
        if self.owns_client:
            await self.client.aclose()

    def url(self, path: str) -> str:
        return path if httpx.URL(path).is_absolute_url else f"{self.base_url}/{path.lstrip('/')}"

    async def throttle(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            async with self.lock:
                now = loop.time()
                while self.timestamps and now - self.timestamps[0] >= 1:
                    self.timestamps.popleft()
                if len(self.timestamps) < 5:
                    self.timestamps.append(now)
                    return
                delay = 1 - (now - self.timestamps[0])
            await asyncio.sleep(max(delay, 0))

    async def get(self, path: str, params: Mapping[str, Any] | None = None) -> FHIRResource:
        for attempt in range(1, 5):
            try:
                await self.throttle()
                response = await self.client.get(self.url(path), params=params, headers=self.headers)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                if not isinstance(payload, dict):
                    raise ValueError("FHIR response must be a JSON object")
                return payload
            except Exception as error:
                if attempt == 4 or not _retryable(error):
                    raise
                await asyncio.sleep(_retry_wait(error, attempt))
        raise RuntimeError("FHIR request failed")

    async def all(self, path: str, params: Mapping[str, Any] | None = None) -> list[FHIRResource]:
        resources: list[FHIRResource] = []
        url: str | None = self.url(path)
        page_params = params
        while url:
            bundle = await self.get(url, page_params)
            resources.extend(bundle_resources(bundle))
            next_link = next_bundle_link(bundle)
            url = urljoin(url, next_link) if next_link else None
            page_params = None
        return resources

    async def page(self, path: str, page: int, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        url: str | None = self.url(path)
        page_params = params
        current = 1
        while url:
            bundle = await self.get(url, page_params)
            next_link = next_bundle_link(bundle)
            if current == page:
                return {"resources": bundle_resources(bundle), "has_next": bool(next_link)}
            url = urljoin(url, next_link) if next_link else None
            page_params = None
            current += 1
        return {"resources": [], "has_next": False}


def _retryable(error: BaseException) -> bool:
    return isinstance(error, httpx.TransportError) or (
        isinstance(error, httpx.HTTPStatusError) and error.response.status_code in RETRYABLE
    )


def _retry_wait(error: BaseException, attempt: int) -> float:
    if isinstance(error, httpx.HTTPStatusError):
        value = error.response.headers.get("Retry-After")
        if value:
            try:
                return max(0, float(value))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return max(0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
    return float(min(2 ** max(attempt - 1, 0), 8))


def bundle_resources(bundle: Mapping[str, Any]) -> list[FHIRResource]:
    entries = bundle.get("entry")
    if not isinstance(entries, list):
        return []
    return [entry["resource"] for entry in entries if isinstance(entry, dict) and isinstance(entry.get("resource"), dict)]


def next_bundle_link(bundle: Mapping[str, Any]) -> str | None:
    links = bundle.get("link")
    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict) and link.get("relation") == "next" and isinstance(link.get("url"), str):
                return link["url"]
    return None


async def fetch_patients(client: FHIRClient) -> list[FHIRResource]:
    return await client.all("Patient", {"_count": 5})


async def fetch_patient(client: FHIRClient, patient_id: str) -> FHIRResource:
    return await client.get(f"Patient/{quote(patient_id, safe='')}")


async def fetch_conditions(client: FHIRClient, patient_id: str) -> list[FHIRResource]:
    return await client.all("Condition", {"patient": patient_id, "_count": 50})


async def fetch_medications(client: FHIRClient, patient_id: str) -> list[FHIRResource]:
    return await client.all("MedicationRequest", {"patient": patient_id, "_count": 50})
