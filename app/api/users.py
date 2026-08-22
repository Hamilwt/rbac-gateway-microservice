from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.api.deps import get_current_user, require_permissions

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the currently logged-in user's profile.
    Any valid JWT access token can access this.
    """
    return current_user

@router.get("", response_model=List[UserResponse])
def read_all_users(
    db: Session = Depends(get_db),
    # THIS IS THE RBAC MAGIC! 
    # It intercepts the request and checks the token for this exact string.
    token_payload: dict = Depends(require_permissions(["users:read"])) 
):
    """
    Retrieve a list of all users. 
    STRICTLY requires the 'users:read' permission.
    """
    users = db.query(User).all()
    return users