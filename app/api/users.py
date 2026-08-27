from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])

# Schema for incoming role assignments
class UserRoleUpdate(BaseModel):
    roles: list[str]  # A list of role names (e.g., ["admin", "manager"])

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the currently logged-in user's profile.
    Any valid JWT access token can access this.
    """
    return current_user


@router.get("", response_model=list[UserResponse])
def read_all_users(
    db: Session = Depends(get_db),
    # THIS IS THE RBAC MAGIC!
    # It intercepts the request and checks the token for this exact string.
    token_payload: dict = Depends(require_permissions(["users:read"])),
):
    """
    Retrieve a list of all users.
    STRICTLY requires the 'users:read' permission.
    """
    users = db.query(User).all()
    return users


@router.patch("/{user_id}/roles", response_model=UserResponse)
def assign_user_roles(
    user_id: int,
    role_in: UserRoleUpdate,
    db: Session = Depends(get_db),
    # RBAC Guard: Only users with 'roles:assign' can access this
    token_payload: dict = Depends(require_permissions(["roles:assign"]))
):
    """
    Assign roles to a specific user. Overwrites their current roles.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Fetch the requested roles from the database
    new_roles = db.query(Role).filter(Role.name.in_(role_in.roles)).all()
    
    # Verify all requested roles actually exist
    if len(new_roles) != len(role_in.roles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="One or more invalid role names provided"
        )

    # Assign the roles, commit, and return the updated user
    user.roles = new_roles
    db.commit()
    db.refresh(user)
    
    return user