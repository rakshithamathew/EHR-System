from urllib.parse import quote

import httpx

from app.connectors.base import FHIRConnector
from app.core.config import settings
from app.utils.fhir import FHIRPage, FHIRResource

DEFAULT_ORACLE_PATIENT_SEARCH = "smart"


class OracleConnector(FHIRConnector):
    """Connector for the public Oracle Health FHIR R4 sandbox."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float | httpx.Timeout = 30.0,
        max_attempts: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        configured_base_url = base_url or settings.oracle_fhir_base_url
        if not configured_base_url:
            raise ValueError("ORACLE_FHIR_BASE_URL must be configured")

        super().__init__(
            base_url=configured_base_url,
            timeout=timeout,
            max_attempts=max_attempts,
            client=client,
        )

    async def get_patient(self, patient_external_id: str) -> FHIRResource:
        return await self._get(
            f"Patient/{quote(patient_external_id, safe='')}"
        )

    async def get_patients(self) -> list[FHIRResource]:
        return await self._get_paginated(
            "Patient",
            params={
                "_count": 5,
                "name": DEFAULT_ORACLE_PATIENT_SEARCH,
            },
        )

    async def get_patient_page(
        self,
        *,
        page: int,
        count: int,
        search: str | None = None,
    ) -> FHIRPage:
        params: dict[str, str | int] = {
            "_count": count,
            "name": search or DEFAULT_ORACLE_PATIENT_SEARCH,
        }
        return await self._get_page("Patient", page=page, params=params)

    async def get_conditions(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        return await self._get_paginated(
            "Condition",
            params={
                "patient": patient_external_id,
                "_count": 50,
            },
        )

    async def get_medications(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        return await self._get_paginated(
            "MedicationRequest",
            params={
                "patient": patient_external_id,
                "_count": 50,
            },
        )
