"""Auto-generated conftest.py — provides fixtures for db tests."""
import pytest

# ── Register CLI options needed by Agent fixtures ────────────────────────────
def pytest_addoption(parser):
    # Only add if not already registered by another conftest
    try:
        parser.addoption("--product-area", action="store", default="clinical_automation",
                         help="Product area key (from Agent/environments.yaml)")
    except ValueError:
        pass
    try:
        parser.addoption("--env", action="store", default="qa",
                         help="Target environment: dev|qa|crt|prd")
    except ValueError:
        pass


# ── Register markers ────────────────────────────────────────────────────────
def pytest_configure(config):
    config.addinivalue_line("markers", "api: API/REST integration tests")
    config.addinivalue_line("markers", "db: Database/SQL validation tests")
    config.addinivalue_line("markers", "file: File processing/ETL tests")
    config.addinivalue_line("markers", "tidal: Tidal job scheduling tests")
    config.addinivalue_line("markers", "integration: Multi-system integration tests")


# ── Import fixtures from Agent module ───────────────────────────────────────
from Agent.automation_fixtures import (  # noqa: E402, F401
    db_connection, db_cursor
)
