from __future__ import annotations

import pytest

from api.client import ApiClient
from api.config import ApiSettings
from api.headers import build_default_headers


@pytest.mark.api
def test_api_headers_include_required_platform_headers() -> None:
    settings = ApiSettings(
        environment="int",
        base_url="https://example.test",
        application="docuchat-api",
        cs_client_principal="principal-value",
        authorization="Bearer example-token",
        timeout_ms=15000,
        verify_ssl=False,
    )

    headers = build_default_headers(settings)

    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"
    assert headers["Application"] == "docuchat-api"
    assert headers["Cs-Client-Principal"] == "principal-value"
    assert headers["Authorization"] == "Bearer example-token"


@pytest.mark.api
def test_api_client_uses_centralized_headers() -> None:
    settings = ApiSettings(
        environment="int",
        base_url="https://example.test",
        application="docuchat-api",
        cs_client_principal="principal-value",
        timeout_ms=15000,
        verify_ssl=False,
    )
    client = ApiClient(settings)

    try:
        headers = client.build_headers({"X-Correlation-Id": "tc-api-001"})
    finally:
        client.close()

    assert headers["Application"] == "docuchat-api"
    assert headers["Cs-Client-Principal"] == "principal-value"
    assert headers["X-Correlation-Id"] == "tc-api-001"