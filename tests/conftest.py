import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool  # <-- NEW IMPORT

from app.main import app
from app.db.session import get_db

# Import models so Base.metadata knows they exist before create_all
from app.db.base import Base
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission

# Use in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# The StaticPool ensures all connections talk to the SAME in-memory database!
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool  # <-- THIS IS THE MAGIC FIX
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Create all tables before each test
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after each test for a clean slate
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    # Override FastAPI's get_db dependency to use our test database
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    # Clear overrides after the test
    app.dependency_overrides.clear()