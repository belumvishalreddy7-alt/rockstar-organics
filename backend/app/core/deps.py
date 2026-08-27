"""FastAPI dependencies: DB session, current user, role guards."""
from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import User

settings = get_settings()
_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="rso-session")


def _password_stamp(user: User) -> str:
    """A short fingerprint of the user's current password version. Embedding
    this in the session token means a session issued before a password
    change (reset, forced change, or explicit change) stops working even
    though the token itself never expires early otherwise."""
    return user.password_changed_at.isoformat() if user.password_changed_at else ""


def create_session_value(user: User) -> str:
    return _serializer.dumps({"uid": user.id, "pw": _password_stamp(user)})


def read_session_payload(value: str) -> dict | None:
    try:
        return _serializer.loads(value, max_age=settings.SESSION_MAX_AGE_SECONDS)
    except BadSignature:
        return None
    except Exception:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie:
        return None
    payload = read_session_payload(cookie)
    if not payload:
        return None
    user = db.get(User, payload.get("uid"))
    if not user or user.status != "active":
        return None
    if payload.get("pw") != _password_stamp(user):
        # Password changed since this session was issued - reject it.
        return None
    return user


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def require_roles(*roles: str):
    def _dep(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action.")
        return user

    return _dep
