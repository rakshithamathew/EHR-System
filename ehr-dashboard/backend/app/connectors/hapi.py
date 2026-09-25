from urllib.parse import quote

import httpx

from app.connectors.base import FHIRConnector
from app.core.config import settings
from app.utils.fhir import FHIRResource


class HAPIConnector(FHIRConnector):
    """Connector for the public HAPI FHIR R4 test server."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        patient_id: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        configured_base_url = base_url or settings.hapi_fhir_base_url
        if not configured_base_url:
            raise ValueError("HAPI_FHIR_BASE_URL must be configured")

        super().__init__(
            base_url=configured_base_url,
            timeout=timeout,
            client=client,
        )
        configured_patient_id = (
            patient_id if patient_id is not None else settings.hapi_patient_id
        )
        self.patient_id = (
            configured_patient_id.strip() if configured_patient_id else None
        )

    async def get_patients(self) -> list[FHIRResource]:
        if self.patient_id:
            patient = await self._get(
                f"Patient/{quote(self.patient_id, safe='')}"
            )
            if not patient:
                return []
            if patient.get("resourceType") != "Patient":
                raise ValueError("HAPI patient endpoint did not return a Patient")
            return [patient]

        return await self._get_paginated(
            "Patient",
            params={"_count": 20},
        )

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
