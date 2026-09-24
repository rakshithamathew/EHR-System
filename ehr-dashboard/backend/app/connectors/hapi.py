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
        timeout: float | httpx.Timeout = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url or settings.hapi_fhir_base_url,
            timeout=timeout,
            client=client,
        )

    async def get_patients(self) -> list[FHIRResource]:
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
