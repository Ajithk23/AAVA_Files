"""
qtest_defect_client.py
────────────────────────────────────────────────────────────────
Standalone client for submitting Defects via the qTest Manager API.

    POST /api/v3/projects/{projectId}/defects

Completely self-contained — no dependency on any other file in this repo.
Credentials are read from the repository root .env file, or from environment
variables that are already set.

Configuration
─────────────
Set the QTEST_* values in the repository root .env file or in environment
variables before running.

Usage as a module
─────────────────
    from qtest_defect_client import submit_defect

    result = submit_defect(
        properties=[
            {"field_id": 1, "field_value": "Login button broken"},
        ]
    )

Usage as a script (smoke-test)
────────────────────────────────
    python qtest_defect_client.py
"""

from __future__ import annotations

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

import requests
from requests.exceptions import SSLError, RequestException

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = PROJECT_ROOT / ".env"


def _load_dotenv(dotenv_path: Path = DOTENV_PATH) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ[key] = value


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


_load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  ← provide these values via environment variables or root .env
# ─────────────────────────────────────────────────────────────────────────────

QTEST_HOST = _env_first("QTEST_HOST")
QTEST_TOKEN = _env_first("QTEST_TOKEN")
QTEST_PROJECT_ID = _env_first("QTEST_PROJECT_ID")

# SSL – set to a CA cert file path (str) for corporate networks,
#        True to verify with the default bundle, or False to skip (dev only).
QTEST_SSL_VERIFY: bool | str = False

# ─────────────────────────────────────────────────────────────────────────────
# FIELD MAP  ← map each logical field to its numeric qTest field ID
#
# To find a field's ID: in qTest open Project Settings → Defect Fields and
# hover over (or inspect) each field — the ID is shown in the URL / tooltip.
# ─────────────────────────────────────────────────────────────────────────────

FIELD_MAP: dict[str, int] = {
    "summary":     146,   # Summary     (required)
    "description": -20,   # Description (required — built-in negative ID)
    "severity":    345,   # Severity    (value must be a numeric option ID)
    "status":      147,   # Status      (value must be a numeric option ID)
    "priority":    346,   # Priority    (required)
    "type":        -44,   # Type        (required — Bug/Enhancement/etc.)
    "environment": -21,   # Environment (built-in negative ID: option 1=QA, 2=Staging)
}

# Priority option IDs (from qTest Project Settings → Defect Fields → Priority)
_PRIORITY_MEDIUM = 10203   # Medium

# Type option IDs (from qTest Project Settings → Defect Fields → Type)
_TYPE_BUG = 10401          # Bug

# Severity option IDs  (from qTest Project Settings → Defect Fields → Severity)
_SEVERITY_OPTION: dict[str, int] = {
    "Cosmetic": 10301,
    "Minor":    10302,
    "Average":  10303,
    "Major":    10304,  # maps to "High"
    "Fatal":    10305,  # maps to "Critical"
}

# Status option IDs
_STATUS_NEW = 10001  # "New"

# Severity option IDs to assign when a Playwright test fails vs. times out.
# Maps to: Major (10304) for failures, Fatal (10305) for timeouts.
PLAYWRIGHT_FAIL_SEVERITY    = 10304  # Major
PLAYWRIGHT_TIMEOUT_SEVERITY = 10305  # Fatal

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ssl_verify() -> bool | str:
    """Return the QTEST_SSL_VERIFY constant."""
    return QTEST_SSL_VERIFY


def _defect_url(host: str, project_id: int | str) -> str:
    return f"https://{host}/api/v3/projects/{project_id}/defects"


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# Public: build_defect_payload

def build_defect_payload(
    properties: list[dict[str, Any]],
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Assemble a well-formed qTest defect request body without making a
    network call.

    Parameters
    ----------
    properties:
        List of field-value pair dicts.  Each dict must contain at least:
            field_id    (int)  – numeric qTest field ID
            field_value (str)  – value to store
        Optional additional keys:
            field_name       (str)
            field_value_name (str)

    attachments:
        Optional list of attachment objects.  Each should contain:
            name         (str) – file name, e.g. "screenshot.png"
            content_type (str) – MIME type
            data         (str) – base-64 encoded file content

    Returns
    -------
    dict ready to be serialised as the POST body.

    Example
    -------
        payload = build_defect_payload(
            properties=[
                {"field_id": 1,  "field_value": "Login button broken"},
                {"field_id": 18, "field_value": "High"},
            ]
        )
    """
    payload: dict[str, Any] = {"properties": properties}
    if attachments:
        payload["attachments"] = attachments
    return payload


# Public: submit_defect

def submit_defect(
    properties: list[dict[str, Any]],
    attachments: list[dict[str, Any]] | None = None,
    *,
    project_id: int | str | None = None,
    host: str | None = None,
    token: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Submit a new Defect to qTest Manager.

    Credentials fall back to the environment variables / .env file when
    not supplied as arguments.

    Parameters
    ----------
    properties:
        JSONArray of field-value pairs (required by the qTest API).
    attachments:
        Optional JSONArray of Attachment objects.
    project_id:
        Numeric qTest project ID.  Falls back to QTEST_PROJECT_ID.
    host:
        qTest hostname (e.g. ``mycompany.qtestnet.com``).
        Falls back to QTEST_HOST.
    token:
        Bearer token.  Falls back to QTEST_TOKEN.
    timeout:
        HTTP timeout in seconds (default: 30).

    Returns
    -------
    dict
        Parsed JSON response body from qTest (the created Defect object).
        Key fields: ``id``, ``pid``, ``web_url``, ``properties``.

    Raises
    ------
    ValueError
        When required credentials are missing.
    requests.HTTPError
        On 400 / 403 / 500 or any other HTTP error response.
    RuntimeError
        On SSL or network-level failures.
    """
    resolved_host       = (host       or QTEST_HOST).rstrip("/")
    resolved_token      =  token      or QTEST_TOKEN
    resolved_project_id =  project_id or QTEST_PROJECT_ID

    missing: list[str] = []
    if not resolved_host or resolved_host == "mycompany.qtestnet.com":
        missing.append("QTEST_HOST")
    if not resolved_token or resolved_token == "your-bearer-token-here":
        missing.append("QTEST_TOKEN")
    if not resolved_project_id:
        missing.append("QTEST_PROJECT_ID")
    if missing:
        raise ValueError(
            f"Missing required qTest credentials: {', '.join(missing)}. "
            "Edit the CONFIGURATION block at the top of qtest_defect_client.py."
        )

    url = _defect_url(resolved_host, resolved_project_id)
    headers = _auth_headers(resolved_token)
    verify = _ssl_verify()
    payload = build_defect_payload(properties, attachments)

    logger.debug("POST %s  payload=%s", url, json.dumps(payload, default=str))

    # ── Execute HTTP request ──────────────────────────────────
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
            verify=verify,
        )
    except SSLError as exc:
        raise RuntimeError(
            "SSL handshake failed while calling qTest. "
            "Set QTEST_CA_BUNDLE to your CA cert path, or set "
            "QTEST_SSL_VERIFY=false for testing only. "
            f"Original error: {exc}"
        ) from exc
    except RequestException as exc:
        raise RuntimeError(
            f"Network error while submitting defect to qTest: {exc}"
        ) from exc

    # ── Map documented error codes to clear messages ──────────
    if response.status_code == 400:
        raise requests.HTTPError(
            "400 Bad Request – field value constraint is invalid. "
            f"Response: {response.text[:300]}",
            response=response,
        )
    if response.status_code == 403:
        raise requests.HTTPError(
            "403 Forbidden – user does not have permission to submit a defect.",
            response=response,
        )
    if response.status_code == 500:
        raise requests.HTTPError(
            f"500 Internal Server Error from qTest. Response: {response.text[:300]}",
            response=response,
        )

    response.raise_for_status()
    return response.json()


# ─────────────────────────────────────────────────────────────────────────────
# Playwright integration
# ─────────────────────────────────────────────────────────────────────────────

class PlaywrightTestResult(TypedDict, total=False):
    """
    Shape of the test-failure data passed in from Playwright.

    Required
    --------
    title         Full test title, e.g. "Login > should redirect to dashboard"
    error_message The assertion / exception message

    Optional (enriches the defect description)
    -------------------------------------------
    file          Spec file path, e.g. "tests/login.spec.ts"
    stack_trace   Full stack trace string
    browser       Browser name: "chromium" | "firefox" | "webkit"
    status        "failed" | "timedOut" | "interrupted"
    duration_ms   Test duration in milliseconds
    retry         Retry attempt number (0 = first run)
    """
    title:         str
    error_message: str
    file:          str
    stack_trace:   str
    browser:       str
    status:        str
    duration_ms:   int
    retry:         int


def build_playwright_defect_properties(
    result: PlaywrightTestResult,
) -> list[dict[str, Any]]:
    """
    Convert a PlaywrightTestResult dict into a qTest ``properties`` list
    ready to pass to :func:`submit_defect`.

    Field IDs are taken from the FIELD_MAP configuration block.
    Any field whose ID is 0 or absent in FIELD_MAP is silently skipped.
    """
    title         = result.get("title", "Playwright test failure")
    error_message = result.get("error_message", "(no error message)")
    status        = result.get("status", "failed")
    browser       = result.get("browser", "unknown browser")
    spec_file     = result.get("file", "unknown file")
    stack_trace   = result.get("stack_trace", "")
    duration_ms   = result.get("duration_ms")
    retry         = result.get("retry", 0)

    severity_id = (
        PLAYWRIGHT_TIMEOUT_SEVERITY if status == "timedOut"
        else PLAYWRIGHT_FAIL_SEVERITY
    )

    # Build the human-readable description
    duration_str = f"{duration_ms} ms" if duration_ms is not None else "unknown"
    ran_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    description_lines = [
        f"** Automated defect from Playwright — {ran_at} **",
        "",
        f"Test   : {title}",
        f"File   : {spec_file}",
        f"Browser: {browser}",
        f"Status : {status}",
        f"Duration: {duration_str}",
        f"Retry  : {retry}",
        "",
        "--- Error ---",
        error_message,
    ]
    if stack_trace:
        description_lines += ["", "--- Stack Trace ---", stack_trace]

    description = "\n".join(description_lines)

    # Map logical fields → qTest field IDs and their option IDs where required.
    # severity, status, priority, type, environment must be numeric option IDs.
    raw: list[tuple[int, Any]] = [
        (FIELD_MAP.get("summary",     0), f"[Playwright] {title}"),
        (FIELD_MAP.get("description", 0), description),
        (FIELD_MAP.get("severity",    0), severity_id),
        (FIELD_MAP.get("status",      0), _STATUS_NEW),
        (FIELD_MAP.get("priority",    0), _PRIORITY_MEDIUM),
        (FIELD_MAP.get("type",        0), _TYPE_BUG),
    ]

    return [
        {"field_id": fid, "field_value": fvalue}
        for fid, fvalue in raw
        if fid != 0
    ]


def submit_playwright_failure(
    result: PlaywrightTestResult,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    One-call shortcut: convert a Playwright test-failure dict straight into
    a qTest Defect and submit it.

    Parameters
    ----------
    result:
        A :class:`PlaywrightTestResult` dict with at minimum ``title`` and
        ``error_message``.
    **kwargs:
        Forwarded to :func:`submit_defect`  (``project_id``, ``host``,
        ``token``, ``timeout``).

    Returns
    -------
    dict  The created Defect object returned by qTest.

    Example
    -------
        result = submit_playwright_failure({
            "title":         "Checkout > should complete order",
            "error_message": "Expected 'Order confirmed' but got timeout",
            "file":          "tests/checkout.spec.ts",
            "browser":       "chromium",
            "status":        "timedOut",
            "duration_ms":   30000,
        })
        print(result["pid"], result["web_url"])
    """
    properties = build_playwright_defect_properties(result)
    return submit_defect(properties, **kwargs)


def extract_defect_url(result: dict[str, Any]) -> str:
    """Return the direct qTest URL from a defect creation response when present."""
    defect_url = str(result.get("web_url", "") or "").strip()
    if defect_url:
        return defect_url

    for link in result.get("links", []):
        if isinstance(link, dict) and link.get("rel") == "alternate":
            return str(link.get("href", "") or "").strip()

    return ""


# Public: submit_defect_from_dict

def submit_defect_from_dict(defect_dict: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """
    Submit a defect from a pre-built dict that already contains
    ``properties`` (and optionally ``attachments``) keys.

    Extra keyword arguments are forwarded to :func:`submit_defect`.

    Example
    -------
        result = submit_defect_from_dict({
            "properties": [
                {"field_id": 1, "field_value": "Crash on login"}
            ]
        })
    """
    return submit_defect(
        defect_dict.get("properties", []),
        defect_dict.get("attachments"),
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Script entry-point  (quick smoke-test)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )

    # ── Simulated Playwright test failure ─────────────────────
    # In real usage Playwright would populate this dict and call
    # submit_playwright_failure() from a global-setup / reporter hook.
    simulated_failure: PlaywrightTestResult = {
        "title":         "Login > should redirect to dashboard after valid credentials",
        "error_message": "expect(page).toHaveURL('dashboard') – Received: 'home'",
        "file":          "tests/auth/login.spec.ts",
        "stack_trace":   (
            "Error: expect(received).toHaveURL(expected)\n"
            "  at Object.<anonymous> (tests/auth/login.spec.ts:42:5)\n"
            "  at runMicrotasks (<anonymous>)"
        ),
        "browser":    "chromium",
        "status":     "failed",
        "duration_ms": 4830,
        "retry":       0,
    }

    print("Submitting Playwright failure as qTest defect …")
    print(f"  Test : {simulated_failure['title']}")
    print(f"  Error: {simulated_failure['error_message']}")
    print()

    try:
        result = submit_playwright_failure(simulated_failure)
    except (ValueError, RuntimeError, requests.HTTPError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    defect_url = extract_defect_url(result)
    print("Defect created successfully.")
    print(f"  ID  : {result.get('id')}")
    print(f"  PID : {result.get('pid')}")
    print(f"  URL : {defect_url}")
    print()
    print("Full response:")
    print(json.dumps(result, indent=2, default=str))
