"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from app.db import init_db


@pytest.fixture(scope="session", autouse=True)
def _initialise_database():
    """Ensure all tables exist before any test runs (tests that use Session directly)."""
    init_db()
