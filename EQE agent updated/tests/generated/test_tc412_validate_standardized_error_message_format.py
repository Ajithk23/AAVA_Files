"""TC-412 — Validate Standardized Error Message Format

Description    : Verify that all OCR API error responses conform to the defined
                 standardized error message format for consistency.
Pre-condition  : User has access to OCR enterprise API with permissions to invoke
                 OCR requests.
Feature        : OCR Enterprise API - Error Handling
Environment    : QA
qTest ID       : 268923
qTest PID      : TC-412
User Story     : US #696598
"""
from pathlib import Path
import sys

import pytest
import requests as _requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()
    if venv_python.exists() and current_python != venv_python.resolve():
        import subprocess
        raise SystemExit(subprocess.call([str(venv_python), __file__]))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.step_runner import run_step as _run_step

_TC_NAME = "TC-412"

# Expected standardized error response fields
REQUIRED_ERROR_FIELDS = ["errorCode", "errorMessage", "errorDetails"]


async def _run_tc_flow(docuchat_context: dict) -> None:
    settings = docuchat_context["settings"]
    base_url = settings.get("ocr_api_base_url", settings["base_url"]).rstrip("/")
    timeout_s = int(settings["timeout_ms"]) / 1000

    _auth_headers: dict = {
        "Authorization": f"Bearer {settings.get('ocr_api_token', '')}",
        "Content-Type": "application/json",
    }

    _responses: list = []  # collect responses for cross-step validation

    # ── Step 1 — Send OCR request with invalid payload missing required fields
    async def _step_1_invalid_payload() -> None:
        payload = {
            # intentionally omit 'documentType' and other required fields
            "file_content": "base64_encoded_content_here",
        }
        resp = _requests.post(
            f"{base_url}/ocr/process",
            headers=_auth_headers,
            json=payload,
            timeout=timeout_s,
            verify=False,
        )
        assert resp.status_code >= 400, (
            f"Expected error status code, got {resp.status_code}"
        )
        _responses.append(resp)

    await _run_step(
        1, "Send an OCR request with an invalid payload missing required fields",
        _step_1_invalid_payload(), _TC_NAME, page=None,
    )

    # ── Step 2 — Inspect the error response structure
    async def _step_2_inspect_structure() -> None:
        resp = _responses[0]
        body = resp.json()
        for field in REQUIRED_ERROR_FIELDS:
            assert field in body, (
                f"Standardized error field '{field}' missing from response: {body}"
            )
        assert isinstance(body["errorCode"], str), "errorCode must be a string"
        assert isinstance(body["errorMessage"], str), "errorMessage must be a string"
        assert len(body["errorMessage"]) > 0, "errorMessage must not be empty"

    await _run_step(
        2, "Inspect the error response structure",
        _step_2_inspect_structure(), _TC_NAME, page=None,
    )

    # ── Step 3 — Send OCR request with unreadable image
    async def _step_3_unreadable_image() -> None:
        payload = {
            "documentType": "invoice",
            "file_content": "not_a_valid_base64_image_data",
        }
        resp = _requests.post(
            f"{base_url}/ocr/process",
            headers=_auth_headers,
            json=payload,
            timeout=timeout_s,
            verify=False,
        )
        assert resp.status_code >= 400, (
            f"Expected error status code for unreadable image, got {resp.status_code}"
        )
        _responses.append(resp)

    await _run_step(
        3, "Send an OCR request with an unreadable image causing processing failure",
        _step_3_unreadable_image(), _TC_NAME, page=None,
    )

    # ── Step 4 — Validate error response matches standardized format
    async def _step_4_validate_format() -> None:
        resp = _responses[1]
        body = resp.json()
        for field in REQUIRED_ERROR_FIELDS:
            assert field in body, (
                f"Standardized error field '{field}' missing from unreadable image response: {body}"
            )
        # Verify format consistency with first response
        first_body = _responses[0].json()
        assert set(body.keys()) == set(first_body.keys()), (
            f"Error response structure inconsistent: {set(body.keys())} vs {set(first_body.keys())}"
        )

    await _run_step(
        4, "Validate that the error response matches the standardized format",
        _step_4_validate_format(), _TC_NAME, page=None,
    )

    # ── Step 5 — Repeat error invocation for other common errors
    async def _step_5_common_errors() -> None:
        # Missing documentType field specifically
        payload_missing_doctype = {
            "file_content": "c29tZV9jb250ZW50",  # valid base64 but no documentType
        }
        resp = _requests.post(
            f"{base_url}/ocr/process",
            headers=_auth_headers,
            json=payload_missing_doctype,
            timeout=timeout_s,
            verify=False,
        )
        assert resp.status_code >= 400, (
            f"Expected error for missing documentType, got {resp.status_code}"
        )
        body = resp.json()
        for field in REQUIRED_ERROR_FIELDS:
            assert field in body, (
                f"Standardized field '{field}' missing for common error: {body}"
            )
        _responses.append(resp)

    await _run_step(
        5, "Repeat error invocation for other common errors (e.g., missing documentType field)",
        _step_5_common_errors(), _TC_NAME, page=None,
    )

    # ── Step 6 — Log and document any deviations from error message format
    async def _step_6_check_deviations() -> None:
        deviations: list[str] = []
        for i, resp in enumerate(_responses):
            body = resp.json()
            for field in REQUIRED_ERROR_FIELDS:
                if field not in body:
                    deviations.append(
                        f"Response {i+1}: missing field '{field}'"
                    )
        assert not deviations, (
            f"Format deviations found: {deviations}"
        )

    await _run_step(
        6, "Log and document any deviations from the error message format",
        _step_6_check_deviations(), _TC_NAME, page=None,
    )

    # ── Step 7 — Confirm error response codes are meaningful and consistent
    async def _step_7_verify_error_codes() -> None:
        seen_codes: dict[str, int] = {}
        for resp in _responses:
            body = resp.json()
            code = body.get("errorCode", "")
            assert code, f"errorCode is empty in response: {body}"
            assert len(code) > 0, "errorCode must be non-empty"
            seen_codes[code] = seen_codes.get(code, 0) + 1
        # Verify that different error conditions produce distinct error codes
        # (at least 2 distinct codes across our different error scenarios)
        assert len(seen_codes) >= 2, (
            f"Expected distinct error codes for different conditions, "
            f"but only found: {seen_codes}"
        )

    await _run_step(
        7, "Confirm that error response codes are meaningful and consistent across scenarios",
        _step_7_verify_error_codes(), _TC_NAME, page=None,
    )


@pytest.mark.api
@pytest.mark.regression
async def test_validate_standardized_error_message_format(docuchat_context):
    """TC-412: Validate Standardized Error Message Format."""
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "-vv", "-s"]))
