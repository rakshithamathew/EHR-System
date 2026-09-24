from sqlalchemy.orm import Session


class SyncRepository:
    """Sync run query and persistence boundary."""

    def __init__(self, session: Session) -> None:
        self.session = session
