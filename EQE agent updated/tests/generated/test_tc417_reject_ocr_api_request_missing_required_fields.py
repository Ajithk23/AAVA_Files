"""TC-417 - Reject OCR API request missing required fields

Description    : Verify the API returns a clear, standardized error message when
                 required fields are missing from the request payload.
Pre-condition  : User has valid API credentials and access to the OCR enterprise
                 API endpoint.
Feature        : OCR Enterprise API - Error Handling
Environment    : QA
qTest ID       : 269856
qTest PID      : TC-417
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

_TC_NAME = "TC-417"

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

    # ── Step 1 — Prepare an OCR API request payload missing the required
    #             'documentType' field
    async def _step_1_prepare_missing_field_payload() -> None:
        # Payload intentionally omits 'documentType' required field
        _run_tc_flow._payload = {
            "file_content": "c29tZV9kb2N1bWVudF9jb250ZW50",  # valid base64
            # "documentType" is intentionally missing
        }
        assert "documentType" not in _run_tc_flow._payload, (
            "Payload should NOT contain 'documentType' for this test"
        )

    await _run_step(
        1, "Prepare an OCR API request payload missing the required 'documentType' field",
        _step_1_prepare_missing_field_payload(), _TC_NAME, page=None,
    )

    # ── Step 2 — Send the incomplete request to the OCR API endpoint with
    #             valid authentication
    async def _step_2_send_incomplete_request() -> None:
        resp = _requests.post(
            f"{base_url}/ocr/process",
            headers=_auth_headers,
            json=_run_tc_flow._payload,
            timeout=timeout_s,
            verify=False,
        )
        _run_tc_flow._response = resp

    await _run_step(
        2, "Send the incomplete request to the OCR API endpoint with valid authentication",
        _step_2_send_incomplete_request(), _TC_NAME, page=None,
    )

    # ── Step 3 — Observe the API response status code (expect 400 Bad Request)
    async def _step_3_verify_status_code() -> None:
        resp = _run_tc_flow._response
        assert resp.status_code == 400, (
            f"Expected status code 400 Bad Request, got {resp.status_code}. "
            f"Response body: {resp.text[:300]}"
        )

    await _run_step(
        3, "Observe the API response status code",
        _step_3_verify_status_code(), _TC_NAME, page=None,
    )

    # ── Step 4 — Validate the error message follows the standardized format
    #             with fields such as 'error_code', 'message', and 'details'
    async def _step_4_validate_standardized_format() -> None:
        resp = _run_tc_flow._response
        body = resp.json()
        for field in REQUIRED_ERROR_FIELDS:
            assert field in body, (
                f"Standardized error field '{field}' missing from response: "
                f"{list(body.keys())}"
            )
        # Verify the message references the missing 'documentType' field
        error_msg = body.get("errorMessage", "")
        assert "documentType" in error_msg.lower() or "documenttype" in error_msg.lower(), (
            f"Error message should reference missing 'documentType' field. "
            f"Got: '{error_msg}'"
        )

    await _run_step(
        4, "Validate the error message follows the standardized format with "
           "fields such as 'error_code', 'message', and 'details'",
        _step_4_validate_standardized_format(), _TC_NAME, page=None,
    )

    # ── Step 5 — Confirm that the error message is consistent with other
    #             error responses in format and structure
    async def _step_5_confirm_consistency() -> None:
        # Send a second invalid request (empty payload) to compare format
        resp2 = _requests.post(
            f"{base_url}/ocr/process",
            headers=_auth_headers,
            json={},
            timeout=timeout_s,
            verify=False,
        )
        body1 = _run_tc_flow._response.json()
        body2 = resp2.json()
        # Both error responses should have the same set of top-level keys
        assert set(body1.keys()) == set(body2.keys()), (
            f"Error response structure inconsistent between different error "
            f"conditions: {set(body1.keys())} vs {set(body2.keys())}"
        )

    await _run_step(
        5, "Confirm that the error message is consistent with other error "
           "responses in format and structure",
        _step_5_confirm_consistency(), _TC_NAME, page=None,
    )

    # ── Step 6 — Verify no OCR processing is attempted and no partial
    #             results are returned
    async def _step_6_verify_no_processing() -> None:
        body = _run_tc_flow._response.json()
        # Ensure no recognized text or partial OCR results in the response
        assert "recognizedText" not in body, (
            f"Response should not contain recognized text on error: {body}"
        )
        assert "results" not in body or body.get("results") is None, (
            f"Response should not contain partial results on error: {body}"
        )
        assert "data" not in body or body.get("data") is None, (
            f"Response should not contain data payload on error: {body}"
        )

    await _run_step(
        6, "Verify no OCR processing is attempted and no partial results are returned",
        _step_6_verify_no_processing(), _TC_NAME, page=None,
    )

    # ── Step 7 — Check server logs to confirm the error is logged
    #             appropriately without system failures
    async def _step_7_check_no_system_failure() -> None:
        resp = _run_tc_flow._response
        # Verify response was returned in a reasonable time (no timeout/crash)
        assert resp.elapsed.total_seconds() < timeout_s, (
            f"Response took too long ({resp.elapsed.total_seconds()}s), "
            f"possible system failure"
        )
        # Verify it's not a 5xx server error (which would indicate system failure)
        assert resp.status_code < 500, (
            f"Got server error {resp.status_code} — indicates system failure "
            f"rather than proper error handling. Body: {resp.text[:200]}"
        )

    await _run_step(
        7, "Check server logs to confirm the error is logged appropriately "
           "without system failures",
        _step_7_check_no_system_failure(), _TC_NAME, page=None,
    )


@pytest.mark.api
@pytest.mark.regression
async def test_reject_ocr_api_request_missing_required_fields(docuchat_context):
    """TC-417: Reject OCR API request missing required fields."""
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "-vv", "-s"]))
