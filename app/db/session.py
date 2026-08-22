from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# We use the sync engine (psycopg2) as per the project spec. 
# pool_pre_ping=True tests the connection before using it, preventing dropped connection errors.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# SessionLocal will be used in FastAPI dependencies to give each request its own database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency that yields a database session and safely closes it 
    when the HTTP request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()