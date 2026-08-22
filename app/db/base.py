from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    All our SQLAlchemy models will inherit from this Base.
    This allows Alembic (our migration tool) to find all our tables automatically.
    """
    pass