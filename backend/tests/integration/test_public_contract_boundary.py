"""Public contract isolation from SQLAlchemy persistence models."""

from __future__ import annotations

import inspect

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase

from backend.app.contracts import core
from backend.app.infrastructure.db import models


def test_public_pydantic_contracts_are_never_sqlalchemy_orm_models() -> None:
    """CONTRACT MODULE -> inspect exported model classes -> Pydantic only, never ORM."""
    contract_models = [
        value
        for _, value in inspect.getmembers(core, inspect.isclass)
        if value.__module__ == core.__name__ and issubclass(value, BaseModel)
    ]
    orm_models = [
        value
        for _, value in inspect.getmembers(models, inspect.isclass)
        if value.__module__ == models.__name__ and issubclass(value, DeclarativeBase)
    ]

    assert contract_models
    assert orm_models
    assert set(contract_models).isdisjoint(orm_models)
    assert all(not hasattr(model, "__table__") for model in contract_models)
    assert all(not issubclass(model, BaseModel) for model in orm_models)
