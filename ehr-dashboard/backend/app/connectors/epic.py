from urllib.parse import quote

import httpx

from app.connectors.base import FHIRConnector
from app.core.config import settings
from app.utils.fhir import FHIRPage, FHIRResource


class EpicConnectorError(RuntimeError):
    """Base error for unavailable Epic connector operations."""


class EpicAuthorizationRequiredError(EpicConnectorError):
    """Raised when no active Epic SMART access token is available."""


class EpicFHIRConnector(FHIRConnector):
    """Placeholder connector for protected Epic FHIR R4 APIs."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        client_id: str | None = None,
        redirect_uri: str | None = None,
        authorization_url: str | None = None,
        token_url: str | None = None,
        access_token: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.epic_fhir_base_url = base_url or settings.epic_fhir_base_url
        self.epic_client_id = client_id or settings.epic_client_id
        self.epic_redirect_uri = redirect_uri or settings.epic_redirect_uri
        self.epic_authorization_url = (
            authorization_url or settings.epic_authorization_url
        )
        self.epic_token_url = token_url or settings.epic_token_url
        self.access_token = access_token

        if not self.epic_fhir_base_url:
            raise ValueError("EPIC_FHIR_BASE_URL must be configured")
        super().__init__(
            base_url=self.epic_fhir_base_url,
            timeout=timeout,
            client=client,
        )

    def _authorization_headers(self) -> dict[str, str]:
        if not self.access_token:
            raise EpicAuthorizationRequiredError(
                "Connect Epic before loading its patient data"
            )
        return {"Authorization": f"Bearer {self.access_token}"}

    async def get_patients(self) -> list[FHIRResource]:
        return await self._get_paginated(
            "Patient",
            params={"_count": 20},
            headers=self._authorization_headers(),
        )

    async def get_patient(self, patient_external_id: str) -> FHIRResource:
        return await self._get(
            f"Patient/{quote(patient_external_id, safe='')}",
            headers=self._authorization_headers(),
        )

    async def get_patient_page(
        self,
        *,
        page: int,
        count: int,
        search: str | None = None,
    ) -> FHIRPage:
        params: dict[str, str | int] = {"_count": count}
        if search:
            params["name"] = search
        return await self._get_page(
            "Patient",
            page=page,
            params=params,
            headers=self._authorization_headers(),
        )

    async def get_conditions(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        return await self._get_paginated(
            "Condition",
            params={"patient": patient_external_id, "_count": 50},
            headers=self._authorization_headers(),
        )

    async def get_medications(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        return await self._get_paginated(
            "MedicationRequest",
            params={"patient": patient_external_id, "_count": 50},
            headers=self._authorization_headers(),
        )
