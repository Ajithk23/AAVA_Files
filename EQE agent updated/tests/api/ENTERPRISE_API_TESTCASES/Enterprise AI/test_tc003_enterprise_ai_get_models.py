from __future__ import annotations

from dataclasses import replace

import pytest

from api.client import ApiClient
from api.config import ApiSettings
from api.validators import assert_json_content_type, assert_response_keys


TEST_CASE_NAME = "TC003_Enterprise_AI_Models_GET"
TEST_CASE_DESCRIPTION = (
    "Retrieves the Enterprise AI model list and validates the 200 response contract."
)
ENDPOINT = "/enterprise/ai/v1/models/"
EXPECTED_STATUS_CODE = 200


def _normalize_enterprise_base_url(base_url: str) -> str:
    marker = "/enterprise/docs/"
    if marker in base_url:
        return base_url.split(marker, 1)[0].rstrip("/")
    return base_url.rstrip("/")


@pytest.fixture(scope="session")
def enterprise_api_client() -> ApiClient:
    settings = ApiSettings.from_sources(profile="enterprise")
    settings = replace(settings, base_url=_normalize_enterprise_base_url(settings.base_url))

    missing = settings.missing_required_values()
    if missing:
        pytest.skip(
            "Enterprise API runtime configuration is incomplete. Missing: " + ", ".join(missing),
            allow_module_level=True,
        )

    client = ApiClient(settings)
    yield client
    client.close()


@pytest.mark.api
@pytest.mark.api_integration
def test_enterprise_ai_get_models(enterprise_api_client: ApiClient) -> None:
    """Retrieves Enterprise AI models and validates the 200 response body."""
    response = enterprise_api_client.get(
        ENDPOINT,
        expected_status=EXPECTED_STATUS_CODE,
    )

    assert response.status_code == EXPECTED_STATUS_CODE
    assert_json_content_type(response)

    payload = enterprise_api_client.response_json(response)
    assert isinstance(payload, dict)
    assert_response_keys(payload, ["object", "data"])

    assert payload["object"] == "list"
    assert isinstance(payload["data"], list)

    for model in payload["data"]:
        assert isinstance(model, dict)
        assert_response_keys(model, ["id", "description", "provider", "display_order"])
        assert isinstance(model["id"], str)
        assert model["id"]
        assert isinstance(model["description"], str)
        assert isinstance(model["provider"], str)
        assert isinstance(model["display_order"], int)


test_enterprise_ai_get_models.test_case_name = TEST_CASE_NAME
test_enterprise_ai_get_models.test_case_description = TEST_CASE_DESCRIPTION


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "-vv", "-s"]))