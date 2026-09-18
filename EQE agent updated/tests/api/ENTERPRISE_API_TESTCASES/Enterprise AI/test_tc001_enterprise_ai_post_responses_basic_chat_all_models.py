from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from api.client import ApiClient
from api.config import ApiSettings
from api.validators import assert_json_content_type, assert_response_keys


ENDPOINT = "/enterprise/ai/v1/responses/"
EXPECTED_STATUS_CODE = 200


def _normalize_enterprise_base_url(base_url: str) -> str:
    marker = "/enterprise/docs/"
    if marker in base_url:
        return base_url.split(marker, 1)[0].rstrip("/")
    return base_url.rstrip("/")


def _enterprise_settings() -> ApiSettings:
    settings = ApiSettings.from_sources(profile="enterprise")
    return replace(settings, base_url=_normalize_enterprise_base_url(settings.base_url))


def _sanitize_case_name(value: str) -> str:
    sanitized = "".join(character if character.isalnum() else "_" for character in value.strip())
    sanitized = "_".join(part for part in sanitized.split("_") if part)
    return sanitized or "UNKNOWN_MODEL"


def _load_model_variants() -> list[pytest.ParamSpecArgs]:
    settings = _enterprise_settings()
    missing = settings.missing_required_values()
    if missing:
        return [
            pytest.param(
                None,
                None,
                marks=pytest.mark.skip(
                    reason="Enterprise API configuration is incomplete. Missing: " + ", ".join(missing)
                ),
                id="TC001_ENTERPRISE_CONFIG_POST",
            )
        ]

    client = ApiClient(settings)
    try:
        response = client.get("/enterprise/ai/v1/models/", expected_status=200)
        payload = client.response_json(response)
    except Exception as exc:  # noqa: BLE001
        return [
            pytest.param(
                None,
                None,
                marks=pytest.mark.skip(reason=f"Unable to discover Enterprise AI models: {exc}"),
                id="TC001_MODEL_DISCOVERY_POST",
            )
        ]
    finally:
        client.close()

    models = payload.get("data", []) if isinstance(payload, dict) else []
    if not models:
        return [
            pytest.param(
                None,
                None,
                marks=pytest.mark.skip(reason="Enterprise AI models endpoint returned no models."),
                id="TC001_NO_MODELS_POST",
            )
        ]

    variants = []
    for item in models:
        model_id = item.get("id", "") if isinstance(item, dict) else ""
        model_name = item.get("description", model_id) if isinstance(item, dict) else ""
        case_id = f"TC001_{_sanitize_case_name(model_name or model_id)}_POST"
        variants.append(pytest.param(model_id, model_name, id=case_id))
    return variants


_MODEL_VARIANTS = _load_model_variants()


@pytest.fixture(scope="session")
def enterprise_api_client() -> ApiClient:
    settings = _enterprise_settings()
    missing = settings.missing_required_values()
    if missing:
        pytest.skip(
            "Enterprise API runtime configuration is incomplete. Missing: " + ", ".join(missing),
            allow_module_level=True,
        )

    client = ApiClient(settings)
    yield client
    client.close()


def _build_basic_chat_payload(model_id: str) -> dict[str, Any]:
    return {
        "model": model_id,
        "input": "Reply with the single word PASS.",
        "store": True,
        "max_output_tokens": 50,
    }


@pytest.mark.api
@pytest.mark.api_integration
@pytest.mark.parametrize("model_id, model_name", _MODEL_VARIANTS)
def test_enterprise_ai_post_responses_basic_chat_all_models(
    enterprise_api_client: ApiClient,
    model_id: str | None,
    model_name: str | None,
) -> None:
    """Posts a basic chat request to Enterprise AI responses for each discovered model and validates a 200 response contract."""
    if not model_id:
        pytest.skip("No Enterprise AI model available for execution.")

    response = enterprise_api_client.post(
        ENDPOINT,
        json=_build_basic_chat_payload(model_id),
        expected_status=EXPECTED_STATUS_CODE,
    )

    assert response.status_code == EXPECTED_STATUS_CODE
    assert_json_content_type(response)

    payload = enterprise_api_client.response_json(response)
    assert isinstance(payload, dict)
    assert_response_keys(
        payload,
        [
            "id",
            "object",
            "status",
            "model",
            "output",
            "usage",
            "created_at",
            "completed_at",
            "correlation_id",
        ],
    )

    assert payload["id"].startswith("resp_")
    assert payload["object"] == "response"
    assert payload["status"] == "completed"
    assert payload["model"] == model_id
    assert isinstance(payload["output"], list)
    assert isinstance(payload["usage"], dict)
    assert_response_keys(payload["usage"], ["input_tokens", "output_tokens", "total_tokens"])
    assert isinstance(payload["usage"]["input_tokens"], int)
    assert isinstance(payload["usage"]["output_tokens"], int)
    assert isinstance(payload["usage"]["total_tokens"], int)
    assert payload["correlation_id"]
    assert payload["created_at"]
    assert payload["completed_at"]

    if payload["output"]:
        first_output = payload["output"][0]
        assert isinstance(first_output, dict)
        assert_response_keys(first_output, ["id", "type"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "-vv", "-s"]))