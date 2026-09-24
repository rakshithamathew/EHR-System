from sqlalchemy.orm import Session


class PatientRepository:
    """Patient query and upsert boundary."""

    def __init__(self, session: Session) -> None:
        self.session = session
