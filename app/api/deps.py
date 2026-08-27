import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# This tells FastAPI where clients should send their credentials to get a token.
# It automatically powers the "Authorize" button in the Swagger UI.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    Dependency to validate the JWT and return the database user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the token using our secret key
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    # Fetch user from DB
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def get_optional_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """
    Like get_current_user, but returns None instead of raising 401
    when there's no valid token. Used by the rate limiter so it can
    key by user_id when authenticated, and fall back to IP otherwise.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except InvalidTokenError:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()


def require_permissions(required_permissions: list[str]):
    """
    A factory function that returns a dependency.
    It checks if the user's token contains the required permissions.
    """

    def permission_checker(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_perms = payload.get("permissions", [])

            # Check if all required permissions are in the user's token
            for perm in required_permissions:
                if perm not in user_perms:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission: {perm}",
                    )
            return payload
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    return permission_checker