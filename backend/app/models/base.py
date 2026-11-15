"""SQLAlchemy base class."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all tables."""
