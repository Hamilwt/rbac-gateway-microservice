from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict  # <-- Imported ConfigDict

from app.db.session import get_db
from app.models.role import Role
from app.models.permission import Permission
from app.api.deps import require_permissions

router = APIRouter(prefix="/roles", tags=["roles"])

# Pydantic schema for creating a role
class RoleCreate(BaseModel):
    name: str
    permissions: list[str] = []

class RoleResponse(BaseModel):
    id: int
    name: str
    permissions: list[str]

    model_config = ConfigDict(from_attributes=True)  # <-- Modern Pydantic V2 syntax

@router.get("", response_model=list[RoleResponse])
def get_roles(
    db: Session = Depends(get_db),
    # RBAC Guard: Only users with 'roles:read' can access this
    token_payload: dict = Depends(require_permissions(["roles:read"]))
):
    """
    List all roles and their associated permissions.
    """
    roles = db.query(Role).all()
    # Format the response to extract permission names
    response = []
    for role in roles:
        response.append({
            "id": role.id,
            "name": role.name,
            "permissions": [p.name for p in role.permissions]
        })
    return response


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    # RBAC Guard: Only users with 'roles:write' can access this
    token_payload: dict = Depends(require_permissions(["roles:write"]))
):
    """
    Create a new role and assign permissions to it.
    """
    # Check if role already exists
    if db.query(Role).filter(Role.name == role_in.name).first():
        raise HTTPException(status_code=400, detail="Role already exists")

    new_role = Role(name=role_in.name)

    # Attach permissions
    if role_in.permissions:
        perms = db.query(Permission).filter(Permission.name.in_(role_in.permissions)).all()
        # Verify all requested permissions actually exist in the database
        if len(perms) != len(role_in.permissions):
            raise HTTPException(status_code=400, detail="One or more permissions are invalid")
        new_role.permissions.extend(perms)

    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    return {
        "id": new_role.id,
        "name": new_role.name,
        "permissions": [p.name for p in new_role.permissions]
    }