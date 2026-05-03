"""
Conftest for unit tests.

Overrides the session-scoped autouse `_test_database_lifecycle` from the
parent conftest so that these tests run without any database connection.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def _test_database_lifecycle():  # type: ignore[override]
    """No-op override: unit tests use mocked sessions, no DB required."""
    yield
