"""
Agent/generated_conftest_template.py — Template conftest for generated non-UI tests
═══════════════════════════════════════════════════════════════════════════════
The TestGenAgent copies this file as conftest.py into the generated test folder.
It registers --product-area, --env options and imports the right fixtures.

This is a TEMPLATE — the agent fills in the product_area default value.
═══════════════════════════════════════════════════════════════════════════════
"""

TEMPLATE = '''"""Auto-generated conftest.py — provides fixtures for {automation_type} tests."""
import pytest

# ── Register CLI options needed by Agent fixtures ────────────────────────────
def pytest_addoption(parser):
    # Only add if not already registered by another conftest
    try:
        parser.addoption("--product-area", action="store", default="{product_area}",
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
    {fixture_imports}
)
'''


def render(automation_type: str, product_area: str) -> str:
    """
    Render the conftest template for a given automation type.

    Args:
        automation_type: "api" | "db" | "file" | "tidal" | "hybrid"
        product_area: key from environments.yaml (e.g. "clinical_automation")

    Returns:
        Complete conftest.py file content as a string.
    """
    fixture_map = {
        "api": "api_client",
        "db": "db_connection, db_cursor",
        "file": "file_paths, wait_for_file, wait_for_file_removal",
        "tidal": "tidal_client",
        "hybrid": "api_client, db_connection, db_cursor, tidal_client, file_paths, wait_for_file, wait_for_file_removal",
    }
    imports = fixture_map.get(automation_type, fixture_map["hybrid"])
    return TEMPLATE.format(
        automation_type=automation_type,
        product_area=product_area,
        fixture_imports=imports,
    )
