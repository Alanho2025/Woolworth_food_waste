"""Shared SQLAlchemy declarative base for FoodFlow models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class used to register FoodFlow tables without creating them implicitly."""
