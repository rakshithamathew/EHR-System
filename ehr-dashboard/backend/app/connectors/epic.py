from typing import NoReturn

import httpx

from app.connectors.base import FHIRConnector
from app.core.config import settings
from app.utils.fhir import FHIRResource


class EpicConnectorError(RuntimeError):
    """Base error for unavailable Epic connector operations."""


class EpicConfigurationError(EpicConnectorError):
    """Raised when required Epic SMART on FHIR settings are missing."""


class EpicAuthorizationRequiredError(EpicConnectorError):
    """Raised until the Epic SMART on FHIR OAuth flow is implemented."""


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

        # Epic FHIR APIs require SMART on FHIR OAuth authorization before
        # protected resources can be queried. The reserved URL is never called;
        # it only lets this placeholder initialize before configuration exists.
        super().__init__(
            base_url=self.epic_fhir_base_url or "https://epic.invalid/fhir",
            timeout=timeout,
            client=client,
        )

    def _require_oauth_authorization(self) -> NoReturn:
        configuration = {
            "EPIC_FHIR_BASE_URL": self.epic_fhir_base_url,
            "EPIC_CLIENT_ID": self.epic_client_id,
            "EPIC_REDIRECT_URI": self.epic_redirect_uri,
            "EPIC_AUTHORIZATION_URL": self.epic_authorization_url,
            "EPIC_TOKEN_URL": self.epic_token_url,
        }
        missing = [
            name
            for name, value in configuration.items()
            if value is None or not value.strip()
        ]

        if missing:
            raise EpicConfigurationError(
                "Epic SMART on FHIR configuration is incomplete. Missing: "
                + ", ".join(missing)
            )

        raise EpicAuthorizationRequiredError(
            "Epic SMART on FHIR OAuth authorization is required before "
            "protected FHIR APIs can be queried; OAuth is not implemented yet."
        )

    async def get_patients(self) -> list[FHIRResource]:
        self._require_oauth_authorization()

    async def get_conditions(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        self._require_oauth_authorization()

    async def get_medications(
        self,
        patient_external_id: str,
    ) -> list[FHIRResource]:
        self._require_oauth_authorization()
