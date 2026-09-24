from app.connectors.base import FHIRConnector


class FHIRService:
    """FHIR retrieval and normalization boundary."""

    def __init__(self, connector: FHIRConnector) -> None:
        self.connector = connector
