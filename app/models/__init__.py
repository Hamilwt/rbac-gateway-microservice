# Import the Base and all models so Alembic can read them from one place
from app.db.base import Base
from app.models.permission import Permission
from app.models.role import Role, role_permissions
from app.models.user import User, user_roles
