from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    # This tells Pydantic to read data directly from the SQLAlchemy model
    model_config = {"from_attributes": True}
