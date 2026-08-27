import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt directly (no passlib)."""
    salt = bcrypt.gensalt()
    # bcrypt requires bytes, so we encode the string
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against the hashed version."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(subject: str | int, permissions: list[str]) -> str:
    """
    Generate a short-lived JWT access token.
    We embed the user's permissions directly in the token payload.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"exp": expire, "sub": str(subject), "permissions": permissions}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(subject: str | int) -> str:
    """
    Generate a long-lived JWT refresh token with a unique 'jti' identifier.
    This 'jti' is what we will track in Redis later for revocation.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    jti = str(uuid.uuid4())
    to_encode = {"exp": expire, "sub": str(subject), "jti": jti, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt
