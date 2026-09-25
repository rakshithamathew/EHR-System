from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception, stop_after_attempt

from app.utils.fhir import (
    FHIRPage,
    FHIRQueryParams,
    FHIRResource,
    fetch_fhir_bundle_page,
    paginate_fhir_bundle,
)

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 4


def _is_retryable_error(exception: BaseException) -> bool:
    if isinstance(exception, httpx.TransportError):
        return True

    return (
        isinstance(exception, httpx.HTTPStatusError)
        and exception.response.status_code in _RETRYABLE_STATUS_CODES
    )


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)

    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _retry_wait(retry_state: RetryCallState) -> float:
    exception = (
        retry_state.outcome.exception()
        if retry_state.outcome is not None
        else None
    )

    if isinstance(exception, httpx.HTTPStatusError):
        retry_after = _parse_retry_after(
            exception.response.headers.get("Retry-After")
        )
        if retry_after is not None:
            return retry_after

    return float(min(2 ** max(retry_state.attempt_number - 1, 0), 8))


class FHIRConnector(ABC):
    """Shared contract and HTTP transport for provider FHIR connectors."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float | httpx.Timeout = 30.0,
        max_attempts: int = _MAX_ATTEMPTS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        if max_attempts < 1 or max_attempts > _MAX_ATTEMPTS:
            raise ValueError(f"max_attempts must be between 1 and {_MAX_ATTEMPTS}")

        self.base_url = base_url.rstrip("/")
        self.timeout = (
            timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
        )
        self.max_attempts = max_attempts
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "FHIRConnector":
        self._get_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()

        return self._client

    def _build_url(self, path: str) -> str:
        url = httpx.URL(path)
        if url.is_absolute_url:
            return str(url)

        return f"{self.base_url}/{path.lstrip('/')}"

    async def _get(
        self,
        path: str,
        *,
        params: FHIRQueryParams | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> FHIRResource:
        """Perform a FHIR GET with bounded retries for temporary failures."""

        request_headers = {"Accept": "application/fhir+json"}
        if headers is not None:
            request_headers.update(headers)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable_error),
            wait=_retry_wait,
            stop=stop_after_attempt(self.max_attempts),
            reraise=True,
        ):
            with attempt:
                response = await self._get_client().get(
                    self._build_url(path),
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                if not response.content:
                    return {}

                payload = response.json()

                if not isinstance(payload, dict):
                    raise ValueError("FHIR endpoint returned a non-object JSON payload")

                return payload

        raise RuntimeError("FHIR GET retry loop exited without a response")

    async def _get_paginated(
        self,
        path: str,
        *,
        params: FHIRQueryParams | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> list[FHIRResource]:
        """Collect resources by following the Bundle links supplied by the server."""

        async def fetch_page(
            url: str,
            page_params: FHIRQueryParams | None,
        ) -> FHIRResource:
            return await self._get(
                url,
                params=page_params,
                headers=headers,
            )

        return await paginate_fhir_bundle(
            self._build_url(path),
            fetch_page,
            params=params,
        )

    async def _get_page(
        self,
        path: str,
        *,
        page: int,
        params: FHIRQueryParams | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> FHIRPage:
        """Fetch one Bundle page by following provider-supplied next links."""

        async def fetch_page(
            url: str,
            page_params: FHIRQueryParams | None,
        ) -> FHIRResource:
            return await self._get(url, params=page_params, headers=headers)

        return await fetch_fhir_bundle_page(
            self._build_url(path),
            fetch_page,
            page=page,
            params=params,
        )

    @abstractmethod
    async def get_patient(self, patient_external_id: str) -> FHIRResource:
        """Return one raw Patient resource by provider logical ID."""

    @abstractmethod
    async def get_patient_page(
        self,
        *,
        page: int,
        count: int,
        search: str | None = None,
    ) -> FHIRPage:
        """Return one Patient Bundle page and whether another page exists."""

    @abstractmethod
    async def get_patients(self) -> list[FHIRResource]:
        """Return raw Patient resources from the provider."""

    @abstractmethod
    async def get_conditions(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        """Return raw Condition resources for a provider patient identifier."""

    @abstractmethod
    async def get_medications(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        """Return raw medication resources for a provider patient identifier."""
