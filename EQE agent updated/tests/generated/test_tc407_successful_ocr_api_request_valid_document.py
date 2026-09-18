"""TC-407 — Successful OCR API request with valid document

Description    : Verify that the OCR API processes a valid request successfully
                 and returns extracted text data
Pre-condition  : User has valid API credentials and access to OCR API endpoint;
                 valid supported image/document file available
Feature        : OCR Enterprise API - Error Handling
Environment    : QA
"""
from pathlib import Path
import sys
import time

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

_TC_NAME = "TC-407"
_SLA_SEC = 2.0


async def _run_tc_flow(docuchat_context: dict) -> None:
    settings   = docuchat_context["settings"]
    # TODO: add 'ocr_api_base_url' to your env settings if different from base_url
    base_url   = settings.get("ocr_api_base_url", settings["base_url"]).rstrip("/")
    timeout_s  = int(settings["timeout_ms"]) / 1000

    _auth_token: list[str] = []   # populated by step 1; read by step 3
    _http_resp:  list      = []   # [0] = requests.Response, [1] = elapsed_sec

    # ── Step 1 — Authenticate ─────────────────────────────────────────────
    async def _step_1_authenticate() -> None:
        # TODO: replace auth endpoint / credential keys with actual values from settings
        auth_url = f"{base_url}/auth/token"
        creds = {
            "client_id":     settings.get("ocr_client_id", ""),
            "client_secret": settings.get("ocr_client_secret", ""),
        }
        resp = _requests.post(auth_url, json=creds, timeout=timeout_s)
        assert resp.status_code == 200, (
            f"Auth failed: HTTP {resp.status_code} — {resp.text[:200]}"
        )
        token = resp.json().get("access_token") or resp.json().get("token", "")
        assert token, "Auth response did not contain an access_token."
        _auth_token.append(token)

    await _run_step(
        1, "Authenticate with the OCR API using valid credentials",
        _step_1_authenticate(), _TC_NAME,
    )

    # ── Step 2 — Prepare payload ──────────────────────────────────────────
    async def _step_2_prepare_payload() -> None:
        # TODO: set 'ocr_test_image_path' in settings to point at a real test image
        image_path = Path(
            settings.get("ocr_test_image_path",
                         str(PROJECT_ROOT / "test_data" / "sample.png"))
        )
        assert image_path.exists(), (
            f"Test image not found: {image_path}. "
            "Set 'ocr_test_image_path' in settings or add test_data/sample.png."
        )
        doc_type = settings.get("ocr_document_type", "GENERAL")
        assert doc_type, "documentType must not be empty."
        _http_resp.append({"image_path": image_path, "documentType": doc_type})

    await _run_step(
        2, "Prepare a valid OCR request payload with a supported image file and documentType",
        _step_2_prepare_payload(), _TC_NAME,
    )

    # ── Step 3 — POST to /v1/ocr/process and assert HTTP 200 ───────────────
    async def _step_3_send_request() -> None:
        meta    = _http_resp[0]
        headers = {"Authorization": f"Bearer {_auth_token[0]}"}
        with open(meta["image_path"], "rb") as img:
            start   = time.monotonic()
            resp    = _requests.post(
                f"{base_url}/v1/ocr/process",
                headers=headers,
                files={"file": img},
                data={"documentType": meta["documentType"]},
                timeout=timeout_s,
            )
            elapsed = time.monotonic() - start
        assert resp.status_code == 200, (
            f"Expected HTTP 200, got {resp.status_code} — {resp.text[:300]}"
        )
        _http_resp[0] = resp
        _http_resp.append(elapsed)

    await _run_step(
        3, "Send the OCR request to /v1/ocr/process with the valid payload",
        _step_3_send_request(), _TC_NAME,
    )

    # ── Step 4 — Verify response body fields ──────────────────────────────
    async def _step_4_verify_response_body() -> None:
        body = _http_resp[0].json()
        assert "text" in body, "Response JSON is missing the 'text' field."
        assert "confidenceScore" in body, "Response JSON is missing 'confidenceScore'."
        assert not body.get("error"), (
            f"Unexpected 'error' field in a successful response: {body.get('error')}"
        )

    await _run_step(
        4, "Verify response body contains extracted text data and confidence scores",
        _step_4_verify_response_body(), _TC_NAME,
    )

    # ── Step 5 — Verify SLA response time ─────────────────────────────────
    async def _step_5_verify_response_time() -> None:
        elapsed = _http_resp[1]
        assert elapsed < _SLA_SEC, (
            f"Response time {elapsed:.3f}s exceeded SLA of {_SLA_SEC}s."
        )

    await _run_step(
        5, "Confirm that the response time is within SLA limits (< 2 seconds)",
        _step_5_verify_response_time(), _TC_NAME,
    )

    # ── Step 6 — Verify no error fields in response ───────────────────────
    async def _step_6_verify_no_errors() -> None:
        body        = _http_resp[0].json()
        error_keys  = {"error", "errorCode", "error_code", "errorMessage", "error_message"}
        for key in error_keys & set(body.keys()):
            assert not body[key], (
                f"Error field '{key}' present with value: {body[key]}"
            )

    await _run_step(
        6, "Verify no error messages are present in the response",
        _step_6_verify_no_errors(), _TC_NAME,
    )

    # ── Step 7 — Validate standardized response schema ────────────────────
    async def _step_7_validate_response_schema() -> None:
        body     = _http_resp[0].json()
        required = {"text", "confidenceScore"}
        missing  = required - set(body.keys())
        assert not missing, (
            f"Response JSON is missing required schema fields: {missing}"
        )
        assert isinstance(body["text"], str), "'text' must be a string."
        assert isinstance(body["confidenceScore"], (int, float)), (
            "'confidenceScore' must be numeric."
        )

    await _run_step(
        7, "Validate that the response format follows the standardized API response schema",
        _step_7_validate_response_schema(), _TC_NAME,
    )


@pytest.mark.ocr
@pytest.mark.regression
async def test_successful_ocr_api_request_valid_document(docuchat_context):
    await _run_tc_flow(docuchat_context)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv", "-s"]))
