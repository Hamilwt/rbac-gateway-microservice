from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

# Association table linking Users and Roles (Many-to-Many)
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    # Automatically set the timestamp when a user is created
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to easily access a user's roles
    roles = relationship("Role", secondary=user_roles, lazy="joined")
