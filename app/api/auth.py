from redis.exceptions import RedisError
import time
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import Token, RefreshTokenRequest
from app.schemas.user import UserCreate, UserResponse
from app.services.rate_limiter import rate_limit  # <-- NEW IMPORT

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    request: Request,  # <-- Added for rate limiter IP extraction
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    limit: None = Depends(rate_limit("strict"))  # <-- The strict rate limit guard
):
    # 1. Check if user exists
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Hash password and create user
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_pw)

    # 3. Assign the default 'viewer' role automatically
    viewer_role = db.query(Role).filter(Role.name == "viewer").first()
    if viewer_role:
        new_user.roles.append(viewer_role)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Notice we return the UserResponse model, which strips out the password automatically!
    return new_user


@router.post("/login", response_model=Token)
def login(
    request: Request,  # <-- Added for rate limiter IP extraction
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db),
    limit: None = Depends(rate_limit("strict"))  # <-- The strict rate limit guard
):
    # OAuth2PasswordRequestForm automatically looks for 'username' and 'password' in the request body
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Extract all unique permissions from all roles the user holds
    permissions = []
    for role in user.roles:
        for perm in role.permissions:
            if perm.name not in permissions:
                permissions.append(perm.name)

    # Generate tokens
    access_token = create_access_token(subject=user.id, permissions=permissions)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(body: RefreshTokenRequest):
    """
    Revoke a refresh token by adding its unique 'jti' to Redis.
    """
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        jti = payload.get("jti")

        # Calculate how many seconds until the token expires naturally
        exp = payload.get("exp")

        ttl = int(exp - time.time())

        if ttl > 0:
            # Store the jti in Redis for the remaining lifespan of the token
            redis_client.set(f"bl_{jti}", "revoked", ex=ttl)

        return {"message": "Successfully logged out"}
    except InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid token")


@router.post("/refresh", response_model=Token)
def refresh_access_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Issue a new access token AND a new refresh token (rotation) if the
    refresh token is valid and not blacklisted. The old refresh token's
    jti is blacklisted immediately so it can never be reused.
    """
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        jti = payload.get("jti")
        user_id = payload.get("sub")
        token_type = payload.get("type")
        exp = payload.get("exp")

        if token_type != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")

        # Check Redis to see if this token was already used/revoked
        # Check Redis to see if this token was already used/revoked.
        # Fail CLOSED here (unlike the rate limiter, which fails open):
        # if we can't verify a refresh token hasn't been revoked, the
        # safer choice is to reject it, not silently let it through.
        try:
            is_revoked = redis_client.get(f"bl_{jti}")
        except RedisError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify token status right now. Please try again shortly.",
            )
        if is_revoked:
            raise HTTPException(status_code=401, detail="Token has been revoked")

        # Fetch the user to get their latest permissions
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        permissions = list(
            {perm.name for role in user.roles for perm in role.permissions}
        )

        # --- ROTATION: blacklist the OLD refresh token now that it's used ---
        ttl = int(exp - time.time())
        if ttl > 0:
            redis_client.set(f"bl_{jti}", "revoked", ex=ttl)

        # Issue a brand new access token AND a brand new refresh token
        new_access_token = create_access_token(subject=user.id, permissions=permissions)
        new_refresh_token = create_refresh_token(subject=user.id)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")