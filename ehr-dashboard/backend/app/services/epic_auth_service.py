import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


EPIC_SESSION_COOKIE = "epic_session"
AUTHORIZATION_TTL = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class PendingEpicAuthorization:
    session_id: str
    code_verifier: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class EpicAccessToken:
    value: str
    expires_at: datetime
    patient_id: str | None = None
    scope: str | None = None


class EpicOAuthStore:
    """Small process-local OAuth store for the non-production sandbox."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingEpicAuthorization] = {}
        self._tokens: dict[str, EpicAccessToken] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def begin_authorization(self) -> tuple[str, str, str, str]:
        self._remove_expired()
        state = secrets.token_urlsafe(32)
        session_id = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        self._pending[state] = PendingEpicAuthorization(
            session_id=session_id,
            code_verifier=code_verifier,
            expires_at=self._now() + AUTHORIZATION_TTL,
        )
        return state, session_id, code_verifier, code_challenge

    def consume_authorization(self, state: str) -> PendingEpicAuthorization | None:
        pending = self._pending.pop(state, None)
        if pending is None or pending.expires_at <= self._now():
            return None
        return pending

    def save_token(
        self,
        session_id: str,
        access_token: str,
        *,
        expires_in: int,
        patient_id: str | None,
        scope: str | None,
    ) -> None:
        self._tokens[session_id] = EpicAccessToken(
            value=access_token,
            expires_at=self._now() + timedelta(seconds=max(expires_in - 30, 0)),
            patient_id=patient_id,
            scope=scope,
        )

    def get_token(self, session_id: str | None) -> EpicAccessToken | None:
        if not session_id:
            return None
        token = self._tokens.get(session_id)
        if token is None:
            return None
        if token.expires_at <= self._now():
            self._tokens.pop(session_id, None)
            return None
        return token

    def _remove_expired(self) -> None:
        now = self._now()
        self._pending = {
            state: pending
            for state, pending in self._pending.items()
            if pending.expires_at > now
        }
        self._tokens = {
            session_id: token
            for session_id, token in self._tokens.items()
            if token.expires_at > now
        }


epic_oauth_store = EpicOAuthStore()
