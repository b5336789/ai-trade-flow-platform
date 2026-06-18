"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from sqlmodel import SQLModel

import app.models  # noqa: F401 — register all tables on the metadata before create_all
from app.db import engine


@pytest.fixture(scope="session", autouse=True)
def _initialise_database():
    """Start each test session from a clean schema, deterministically.

    Drop + recreate all tables before any test runs so the suite never depends on a pre-existing
    dev DB. This avoids two real foot-guns for an auto-trading system: schema drift (a new column
    like ``OrderRecord.client_order_id`` missing from an old DB) and cross-run data accumulation
    (e.g. the per-UTC-day order count the portfolio risk guard reads — stale orders could trip the
    ``max_orders_per_day`` gate in unrelated tests). Tests run against the configured
    ``DATABASE_URL`` (a local SQLite file by default).
    """
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
