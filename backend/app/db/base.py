from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    All ORM models inherit from this class.

    Usage in a model file:
        from app.db.base import Base

        class Team(Base):
            __tablename__ = "teams"
            ...

    Alembic's env.py imports this Base so it can detect all models
    and auto-generate migration files when you run:
        alembic revision --autogenerate -m "description"
    """
    pass