from __future__ import annotations

import json
import base64
import os
import platform
import re
import sys
import time
import warnings
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import AsyncGenerator, Dict
from urllib.parse import urlparse

import pytest
import pytest_asyncio
import requests
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from utils.config_loader import load_config, resolve_environment
from utils.history_tracker import append_run_history, append_tc_run_history
from utils.logger import get_logger
from utils.notifications import send_run_summary
from utils.report_archiver import archive_run, prune_old_archives
from utils.run_summary_generator import archive_previous_summaries, generate_run_summary
from utils.version_extractor import extract_app_version_from_page

# qTest defect integration (optional — gracefully disabled if package unavailable)
try:
    from Qtest_connection.Defect import submit_playwright_failure, PlaywrightTestResult as _QtestResult
    _QTEST_AVAILABLE = True
except Exception:  # noqa: BLE001
    _QTEST_AVAILABLE = False


logger = get_logger("conftest")
PROJECT_ROOT = Path(__file__).resolve().parent
SCREENSHOTS_DIR = PROJECT_ROOT / "reports" / "screenshots"

# Unique identifier for this test session (used in screenshot folder structure).
_SESSION_RUN_ID = datetime.now().strftime("RUN_%Y%m%d_%H%M%S")


def _feature_from_nodeid(nodeid: str) -> str:
    """Derive feature folder name from a pytest node id.

    Mapping rules (checked in order):
      - path contains ``/chat/``          -> ``Chat``
      - path contains ``/file``           -> ``File_Management``
      - path contains ``/prompt``         -> ``Prompt_Library``
      - fallback                          -> ``Other``
    """
    lower = nodeid.lower()
    if "/chat/" in lower or "\\\\chat\\\\" in lower:
        return "Chat"
    if "/file" in lower or "\\\\file" in lower:
        return "File_Management"
    if "/prompt" in lower or "\\\\prompt" in lower:
        return "Prompt_Library"
    return "Other"


TEST_CASE_DOCS_DIR = PROJECT_ROOT / "Test_Latest_Run_Details"

# Module-level per-test result collector (populated by pytest_runtest_logreport).
_session_test_results: dict[str, str] = {}  # nodeid -> "PASS" | "FAIL"
# Rich per-test metadata collector (populated by teardown fixture).
_session_test_metadata: dict[str, dict] = {}  # nodeid -> {status, duration_ms, ...}
# Session-level warning collector (populated by pytest_warning_recorded).
_session_warnings: list[str] = []

_FEATURE_DOC_MAP: dict[str, str] = {
    "chat": "Regression_TC_DocuChat_Chat_Plain_English.md",
    "file": "Regression_TC_DocuChat_File_Management_Plain_English.md",
    "prompt": "Regression_TC_DocuChat_Prompt_Library_Plain_English.md",
}
ALLURE_RESULTS_DIR = PROJECT_ROOT / "reports" / "allure-results"
VALIDATIONS_DIR = PROJECT_ROOT / "reports" / "history" / "validations"


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Collect final call-phase outcome and capture log warnings per test."""
    if report.when == "call":
        # Ignore intermediate rerun records; only keep final call outcome.
        if str(getattr(report, "outcome", "")).lower() == "rerun":
            return

        _session_test_results[report.nodeid] = "PASS" if report.passed else "FAIL"

        # Ensure controller-side metadata has final status/duration even under xdist.
        metadata = _session_test_metadata.setdefault(report.nodeid, {})
        metadata["status"] = "PASS" if report.passed else "FAIL"
        metadata["duration_ms"] = round(float(getattr(report, "duration", 0.0)) * 1000.0, 2)

        # Capture failure error message for the summary
        if report.failed and report.longrepr:
            error_text = str(report.longrepr)[:500]
            _session_test_metadata[report.nodeid]["error_message"] = error_text
        elif report.passed and report.nodeid in _session_test_metadata:
            # Clear stale error text when a retry later passes.
            _session_test_metadata[report.nodeid]["error_message"] = ""

        # ── Markers that indicate soft-skips, known issues, or unusual behaviour ──
        _INFO_OBSERVATION_MARKERS = (
            "SOFT-SKIP", "soft-skip", "Soft-skipping",
            "KNOWN ISSUE", "Known Issue",
            "Copy icon not found", "not render the copy element",
            "Regenerate Response", "not render the button",
            "Submit button not found", "pressed Enter as fallback",
            "maxlength_attr=-1", "Character limit NOT enforced",
        )

        # ── Parse [STEP_TIMING] lines → per-test step latencies ──────────
        _step_timing_re = re.compile(
            r"\[STEP_TIMING\]\s+(\S+)\s+\|\s+Step\s+(\d+)\s+\|\s+(.+?)\s+\|\s+latency_ms=([\d.]+)"
        )
        step_timings: list[dict] = []

        def _extract_step_and_warning_data(line: str) -> None:
            """Parse a single log line for step-timing and warning data."""
            stripped = line.strip()
            if not stripped:
                return
            # Step timing
            m = _step_timing_re.search(stripped)
            if m:
                failed = "status=FAILED" in stripped
                step_timings.append({
                    "step": int(m.group(2)),
                    "name": m.group(3).strip(),
                    "latency_ms": float(m.group(4)),
                    "status": "FAIL" if failed else "PASS",
                })
                return  # step-timing lines are not warnings
            # Warnings / observations
            if "WARNING" in stripped:
                if stripped not in _session_warnings:
                    _session_warnings.append(stripped)
            elif any(marker in stripped for marker in _INFO_OBSERVATION_MARKERS):
                if stripped not in _session_warnings:
                    _session_warnings.append(stripped)

        # Capture from caplog
        if hasattr(report, "caplog") and report.caplog:
            for line in report.caplog.splitlines():
                _extract_step_and_warning_data(line)
        # Capture from live log sections
        for section_name, section_content in (report.sections or []):
            if "log" in section_name.lower():
                for line in section_content.splitlines():
                    _extract_step_and_warning_data(line)

        # Deduplicate step timings (caplog and live-log sections overlap)
        _seen: set[tuple] = set()
        _deduped: list[dict] = []
        for st in step_timings:
            key = (st["step"], st["name"], st["latency_ms"])
            if key not in _seen:
                _seen.add(key)
                _deduped.append(st)
        step_timings = _deduped

        # Store step timings into metadata (if metadata already exists from
        # teardown fixture, append; otherwise store for later merge)
        if step_timings:
            if report.nodeid in _session_test_metadata:
                _session_test_metadata[report.nodeid]["step_timings"] = step_timings
            else:
                # Metadata not yet created (teardown runs after logreport for
                # passed tests); store so teardown can merge later
                _session_test_metadata.setdefault(report.nodeid, {})["step_timings"] = step_timings


def _count_tc_steps(content: str, tc_num: str) -> int:
    """Count numbered steps under '### Steps' for a given zero-padded TC number."""
    tc_section_match = re.search(
        rf"## TC{tc_num}\b.*?(?=\n## TC\d+|\Z)",
        content,
        re.DOTALL,
    )
    if not tc_section_match:
        return 0
    section = tc_section_match.group(0)
    steps_section_match = re.search(r"### Steps.*?\n(.*?)(?=\n###|\Z)", section, re.DOTALL)
    if not steps_section_match:
        return 0
    return len(re.findall(r"^\d+\.", steps_section_match.group(1), re.MULTILINE))


def _update_test_case_document(
    doc_path: Path,
    results: dict[str, str],
    env: str,
    total: int,
    passed: int,
    failed: int,
    run_id: str = "",
    run_timestamp: str = "",
) -> None:
    """Replace the Execution Summary (latest run only) and update per-TC Final
    Status sections in a plain-English test case document.

    Only the single latest run is retained in Run History — all older entries
    are replaced on every call so the document always reflects the current run.
    """
    if not doc_path.exists():
        return

    content = doc_path.read_text(encoding="utf-8")

    if not run_timestamp:
        run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not run_id:
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    overall = "PASS" if failed == 0 else "FAIL"

    # ── Build TC-number -> status lookup from this run ────────────────────
    tc_status_map: dict[str, str] = {}
    for node_id, status in results.items():
        func_name = node_id.split("::")[-1]
        tc_match = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
        if tc_match:
            tc_status_map[tc_match.group(1).zfill(3)] = status

    if not tc_status_map:
        return

    # ── Count steps & build per-TC detail lines ───────────────────────────
    tc_summary_lines: list[str] = []
    run_history_parts: list[str] = []

    for tc_num in sorted(tc_status_map):
        status = tc_status_map[tc_num]
        steps_total = _count_tc_steps(content, tc_num)
        if steps_total > 0:
            steps_passed = steps_total if status == "PASS" else 0
            steps_failed = 0 if status == "PASS" else steps_total
            tc_summary_lines.append(
                f"  - TC{tc_num}: Steps={steps_total} | "
                f"Steps Passed={steps_passed} | Steps Failed={steps_failed} | Result={status}"
            )
            run_history_parts.append(f"TC{tc_num}={status} ({steps_passed}/{steps_total} steps)")
        else:
            tc_summary_lines.append(
                f"  - TC{tc_num}: Steps=N/A | Steps Passed=N/A | Steps Failed=N/A | Result={status}"
            )
            run_history_parts.append(f"TC{tc_num}={status}")

    # ── Recalculate not-executed TCs ──────────────────────────────────────
    all_tc_nums_in_doc = re.findall(r"^## TC(\d+)", content, re.MULTILINE)
    not_executed_count = sum(1 for n in all_tc_nums_in_doc if n.zfill(3) not in tc_status_map)
    not_executed_label = f" | Not Executed: {not_executed_count}" if not_executed_count > 0 else ""

    # ── Build replacement Execution Summary block ─────────────────────────
    new_summary = (
        "## Execution Summary\n"
        f"- Run ID: {run_id}\n"
        f"- Execution Date/Time: {run_timestamp}\n"
        f"- Environment: {env.upper()}\n"
        f"- Overall Result: {overall}\n"
        f"- Total TCs Run: {total} | Passed: {passed} | Failed: {failed}{not_executed_label}\n"
        f"- TC Details:\n"
        + "\n".join(tc_summary_lines) + "\n"
        "- Note: This document is auto-updated at pytest session end. Only the latest run is retained."
    )

    content = re.sub(
        r"## Execution Summary\n.*?(?=\n## )",
        new_summary + "\n",
        content,
        flags=re.DOTALL,
    )

    # ── Update per-TC Final Status and step Actual results ───────────────
    def _replace_tc_section(match: re.Match) -> str:
        tc_num = match.group(1).zfill(3)
        section = match.group(0)
        if tc_num not in tc_status_map:
            return section
        status = tc_status_map[tc_num]
        section = re.sub(
            r"(### Final Status\s*\n).*",
            lambda m: m.group(1) + status,
            section,
        )
        actual_text = "Passed." if status == "PASS" else "Failed — see run log for details."
        section = re.sub(
            r"(   - Actual:) Not yet executed\.",
            f"\\1 {actual_text}",
            section,
        )
        return section

    content = re.sub(
        r"## TC(\d+)\b.*?(?=\n## TC\d+|\Z)",
        _replace_tc_section,
        content,
        flags=re.DOTALL,
    )

    # ── Single latest-run history line (always Run 1 — only latest is kept) ─
    history_line = (
        f"- Run 1: {run_id} | {run_timestamp} | "
        f"{' | '.join(run_history_parts)} | Overall={overall}"
    )

    # ── Replace ALL previous Run History entries with only this one ───────
    run_history_block = re.search(r"(## Run History\n).*?(?=\n---)", content, re.DOTALL)
    if run_history_block:
        content = (
            content[: run_history_block.start()]
            + f"## Run History\n{history_line}"
            + content[run_history_block.end():]
        )
    else:
        # Fallback: replace or append the full Run History section
        content = re.sub(
            r"## Run History\n.*?(?=\n## |\Z)",
            f"## Run History\n{history_line}\n",
            content,
            flags=re.DOTALL,
        )

    doc_path.write_text(content, encoding="utf-8")
    logger.info("Test case document updated: %s (%s, %s)", doc_path.name, run_id, overall)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--env", action="store", default=None, help="Target environment: dev|qa|uat|int")
    parser.addoption("--headless", action="store", default=None, help="Override headless mode: true|false")
    parser.addoption(
        "--strict-network-validation",
        action="store_true",
        default=False,
        help="Fail tests when network validation detects failed requests or 5xx responses.",
    )
    parser.addoption(
        "--strict-ui-validation",
        action="store_true",
        default=False,
        help="Fail tests when final UI visibility validation fails.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.option.environment = config.getoption("--env")
    config._execution_start_time = time.time()
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _installed_version(name: str) -> str:
    try:
        return package_version(name)
    except PackageNotFoundError:
        return "unknown"


def _extract_app_version(headers: dict[str, str], body: str) -> str:
    header_candidates = (
        "x-app-version",
        "x-version",
        "app-version",
        "x-release",
        "x-build-version",
        "x-deployment-version",
    )
    lowered = {key.lower(): value for key, value in headers.items()}
    for key in header_candidates:
        value = lowered.get(key)
        if value:
            return value.strip()

    patterns = (
        r'(?i)<meta[^>]+name=["\'](?:app-version|application-version|build-version|release)["\'][^>]+content=["\']([^"\']+)["\']',
        r'(?i)(?:app(?:lication)?\s*version|build(?:\s*version)?|release)\s*[:=]\s*["\']?([A-Za-z0-9._-]+)',
        r'(?i)"version"\s*:\s*"([A-Za-z0-9._-]+)"',
    )
    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(1).strip()

    return "unknown"


def _safe_artifact_name(raw: str, max_len: int = 100) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)
    if len(name) > max_len:
        name = name[:max_len]
    return name


def _resolve_ui_automation_env_label(raw_env: str | None, base_url: str | None = None) -> str:
    """Collapse UI automation environment labels to only CRT or INT.

    Rules:
    - INT URL or explicit INT env => ``int``
    - Any other/unspecified UI env defaults to ``crt``
    """
    env_lower = (raw_env or "").strip().lower()
    base_url_lower = (base_url or "").strip().lower()

    if env_lower == "int" or ".int." in base_url_lower:
        return "int"
    return "crt"


def _resolve_run_artifact_env_label(
    raw_env: str | None,
    base_url: str | None = None,
    api_profile: str | None = None,
    collected_items: list[pytest.Item] | None = None,
) -> str:
    profile = (api_profile or "").strip().lower()
    item_paths = [str(item.fspath).replace("\\", "/").lower() for item in (collected_items or [])]
    api_only_run = bool(item_paths) and all("tests/api/" in path for path in item_paths)

    if profile == "enterprise" and api_only_run:
        return "enterprise"

    return _resolve_ui_automation_env_label(raw_env, base_url)


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Dict[str, object]:
    config = load_config()
    env = pytestconfig.getoption("--env")
    resolved = resolve_environment(config, env)

    headless_override = pytestconfig.getoption("--headless")
    if isinstance(headless_override, str):
        resolved["headless"] = headless_override.strip().lower() in {"1", "true", "yes", "y"}

    return resolved


@pytest.fixture(scope="session", autouse=True)
def validate_environment_runtime(settings: Dict[str, object], pytestconfig: pytest.Config) -> Dict[str, object]:
    """Validate runtime/environment once per session and capture app version metadata."""
    base_url = str(settings["base_url"])
    verify_ssl = bool(settings.get("verify_ssl", True))
    timeout_sec = max(int(settings.get("timeout_ms", 15000)) / 1000.0, 5.0)

    start = time.perf_counter()
    try:
        if not verify_ssl:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)
                warnings.filterwarnings("ignore", message=".*Unverified HTTPS request.*")
                response = requests.get(base_url, timeout=timeout_sec, verify=verify_ssl)
        else:
            response = requests.get(base_url, timeout=timeout_sec, verify=verify_ssl)
    except requests.RequestException as exc:
        raise pytest.UsageError(
            f"Environment validation failed: unable to reach base URL {base_url!r}: {exc}"
        ) from exc

    latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
    if response.status_code >= 500:
        raise pytest.UsageError(
            f"Environment validation failed: {base_url!r} returned HTTP {response.status_code}."
        )

    status_is_auth = response.status_code in (401, 403)
    status_note = "(expected for authenticated app)" if status_is_auth else ""

    app_version = _extract_app_version(dict(response.headers), response.text[:300000])
    
    # Check if app version is manually configured
    configured_version = settings.get("app_version")
    if configured_version:
        app_version = str(configured_version)

    runtime_validation = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "environment": str(settings.get("environment", "unknown")),
        "base_url": base_url,
        "base_url_status": response.status_code,
        "base_url_latency_ms": latency_ms,
        "application_version": app_version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "pytest_version": _installed_version("pytest"),
        "playwright_version": _installed_version("playwright"),
    }

    pytestconfig._runtime_validation = runtime_validation

    latest_file = VALIDATIONS_DIR / "latest_validation.json"
    stamped_file = VALIDATIONS_DIR / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    latest_file.write_text(json.dumps(runtime_validation, indent=2), encoding="utf-8")
    stamped_file.write_text(json.dumps(runtime_validation, indent=2), encoding="utf-8")

    logger.info(
        "Runtime validation | env=%s | url=%s | status=%s %s | latency_ms=%.2f | app_version=%s | python=%s | playwright=%s",
        runtime_validation["environment"],
        runtime_validation["base_url"],
        runtime_validation["base_url_status"],
        status_note,
        runtime_validation["base_url_latency_ms"],
        runtime_validation["application_version"],
        runtime_validation["python_version"],
        runtime_validation["playwright_version"],
    )

    return runtime_validation


@pytest_asyncio.fixture
async def playwright_instance() -> AsyncGenerator[Playwright, None]:
    async with async_playwright() as playwright:
        yield playwright


@pytest_asyncio.fixture
async def browser(playwright_instance: Playwright, settings: Dict[str, object]) -> AsyncGenerator[Browser, None]:
    launch_kwargs: Dict[str, object] = {"headless": bool(settings["headless"])}

    # Use system Edge (channel=msedge) for CRT environments that rely on Windows SSO.
    # System Edge inherits OS-level Kerberos/NTLM auth so Okta DSSO works automatically.
    channel = settings.get("channel")
    if channel:
        launch_kwargs["channel"] = str(channel)
        logger.info("Launching browser with channel=%s for Windows SSO support", channel)

    browser = await playwright_instance.chromium.launch(**launch_kwargs)
    yield browser
    await browser.close()


@pytest_asyncio.fixture
async def context(browser: Browser, settings: Dict[str, object]) -> AsyncGenerator[BrowserContext, None]:
    context_kwargs: Dict[str, object] = {
        "base_url": str(settings["base_url"]),
        "ignore_https_errors": not bool(settings.get("verify_ssl", True)),
    }

    # Load storage state for environments that require explicit auth (e.g., INT with Okta MFA)
    auth_config = settings.get("auth")
    if isinstance(auth_config, dict):
        state_path_raw = auth_config.get("storage_state", "")
        if state_path_raw:
            state_path = PROJECT_ROOT / state_path_raw
            if state_path.exists():
                # Check session freshness
                ttl_hours = float(auth_config.get("session_ttl_hours", 4))
                import os
                age_hours = (time.time() - os.path.getmtime(state_path)) / 3600
                if age_hours > ttl_hours:
                    logger.warning(
                        "Storage state is %.1f hours old (TTL=%.0fh). "
                        "Session may have expired. Re-run: python scripts/auth_int_login.py",
                        age_hours, ttl_hours,
                    )
                else:
                    logger.info("Loading storage state from %s (age=%.1fh)", state_path, age_hours)
                context_kwargs["storage_state"] = str(state_path)
            else:
                logger.warning(
                    "Storage state file not found: %s — "
                    "Run 'python scripts/auth_int_login.py' to create it.",
                    state_path,
                )

    browser_context = await browser.new_context(**context_kwargs)
    browser_context.set_default_timeout(int(settings["timeout_ms"]))
    yield browser_context
    await browser_context.close()


@pytest_asyncio.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    page = await context.new_page()
    # Collect browser console messages for diagnostic reporting on failure
    _console_messages: list[str] = []

    def _on_console(msg) -> None:
        _console_messages.append(f"[{msg.type}] {msg.text}")

    page.on("console", _on_console)
    page._diag_console_messages = _console_messages  # type: ignore[attr-defined]
    yield page
    await page.close()


@pytest.fixture
def docuchat_context(page: Page, settings: Dict[str, object]) -> Dict[str, object]:
    return {"page": page, "settings": settings}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Store call report on the item so async fixtures can read it during teardown."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest_asyncio.fixture(autouse=True)
async def execution_quality_checks(
    request: pytest.FixtureRequest,
    page: Page,
    settings: Dict[str, object],
) -> AsyncGenerator[None, None]:
    """Global web-test checks: latency, UI visibility, network validation, and pass/fail screenshots."""
    item_path = Path(str(request.node.fspath)).as_posix().lower()
    if "/tests/web/" not in item_path:
        yield
        return

    runtime_validation: Dict[str, object] = getattr(request.config, "_runtime_validation", {})
    strict_network = bool(request.config.getoption("--strict-network-validation"))
    strict_ui = bool(request.config.getoption("--strict-ui-validation"))

    request_started: dict[int, float] = {}
    failed_requests: list[dict[str, object]] = []
    server_errors: list[dict[str, object]] = []
    response_latencies_ms: list[float] = []
    base_host = urlparse(str(settings.get("base_url", ""))).netloc.lower()

    def _on_request(req) -> None:
        request_started[id(req)] = time.perf_counter()

    def _on_request_failed(req) -> None:
        elapsed_ms = None
        started = request_started.pop(id(req), None)
        if started is not None:
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        request_host = urlparse(req.url).netloc.lower()
        # Validate only first-party traffic to avoid false positives from browser probes/telemetry.
        if base_host and request_host.endswith(base_host):
            failed_requests.append(
                {
                    "method": req.method,
                    "url": req.url,
                    "error": str(req.failure) if req.failure else "unknown",
                    "latency_ms": elapsed_ms,
                }
            )

    def _on_response(resp) -> None:
        started = request_started.pop(id(resp.request), None)
        if started is not None:
            response_latencies_ms.append(round((time.perf_counter() - started) * 1000.0, 2))

        response_host = urlparse(resp.url).netloc.lower()
        if base_host and response_host.endswith(base_host) and resp.status >= 500:
            server_errors.append({"status": resp.status, "url": resp.url, "method": resp.request.method})

    page.on("request", _on_request)
    page.on("requestfailed", _on_request_failed)
    page.on("response", _on_response)

    test_start = time.perf_counter()
    yield

    duration_ms = round((time.perf_counter() - test_start) * 1000.0, 2)
    rep = getattr(request.node, "rep_call", None)
    test_outcome = "passed" if rep and rep.passed else "failed"

    # ── Framework-level failure diagnostics (fires for ANY web test failure) ──
    if test_outcome == "failed" and not page.is_closed():
        try:
            # 1. Browser console messages
            console_msgs: list[str] = getattr(page, "_diag_console_messages", [])
            if console_msgs:
                logger.warning(
                    "[DIAG] Browser console (%d messages) for %s:\n%s",
                    len(console_msgs),
                    request.node.nodeid,
                    "\n".join(console_msgs[-50:]),  # last 50 to keep logs manageable
                )

            # 2. Sidebar button texts (key evidence for chat-history step failures)
            try:
                sidebar_btns = await page.locator(
                    "section[data-testid='stSidebar'] [data-testid='stButton'] button"
                ).all_inner_texts()
                logger.warning(
                    "[DIAG] Sidebar buttons (%d) for %s: %r",
                    len(sidebar_btns),
                    request.node.nodeid,
                    sidebar_btns,
                )
            except Exception as _e:
                logger.warning("[DIAG] Could not read sidebar buttons: %s", _e)

            # 3. Modal status (dialog open/closed + visible text)
            try:
                modal_info = await page.evaluate(
                    """() => {
                        const dlg = document.querySelector('[role="dialog"]');
                        if (!dlg) return null;
                        const rect = dlg.getBoundingClientRect();
                        return {
                            visible: rect.width > 0 && rect.height > 0,
                            text: dlg.innerText.slice(0, 400)
                        };
                    }"""
                )
                logger.warning(
                    "[DIAG] Modal status for %s: %s",
                    request.node.nodeid,
                    modal_info if modal_info else "NO MODAL",
                )
            except Exception as _e:
                logger.warning("[DIAG] Could not read modal status: %s", _e)

            # 4. Active URL and page title
            try:
                logger.warning(
                    "[DIAG] Page URL=%s | title=%s",
                    page.url,
                    await page.title(),
                )
            except Exception as _e:
                logger.warning("[DIAG] Could not read page URL/title: %s", _e)

            # 5. Network summary (failed + 5xx at time of failure)
            logger.warning(
                "[DIAG] Network at failure — failed_requests=%d, server_5xx=%d",
                len(failed_requests),
                len(server_errors),
            )
        except Exception as _diag_err:
            logger.warning("[DIAG] Diagnostic collection itself failed: %s", _diag_err)

    if not page.is_closed() and not hasattr(request.config, "_app_version_captured"):
        should_try_extract = True
        # If version is already configured and not "unknown", skip extraction
        if runtime_validation.get("application_version") and runtime_validation.get("application_version") != "unknown":
            should_try_extract = False
        
        if should_try_extract:
            try:
                captured_version = await extract_app_version_from_page(page, timeout_ms=3000)
                if captured_version:
                    runtime_validation["application_version"] = captured_version
                    setattr(request.config, "_app_version_captured", True)
                    logger.info(
                        "Application version captured from page: %s",
                        captured_version,
                    )
                else:
                    # Debug: capture the page HTML for manual inspection
                    try:
                        page_html = await page.content()
                        version_debug_file = VALIDATIONS_DIR / f"page_version_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                        version_debug_file.write_text(page_html[:500000], encoding="utf-8")
                        logger.debug(
                            "Page snapshot for version debugging saved to: %s. "
                            "Tip: You can set app_version in config.yaml to override automatic detection.",
                            version_debug_file,
                        )
                    except Exception:
                        pass
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to capture app version from page: %s", exc)

    ui_visible = False
    ui_validation_error = ""
    if not page.is_closed():
        try:
            if page.url and not page.url.startswith("about:blank"):
                await page.wait_for_load_state("domcontentloaded", timeout=3000)
            ui_visible = bool(
                await page.evaluate(
                    """
                    () => {
                        const body = document.body;
                        if (!body) return false;
                        const style = window.getComputedStyle(body);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }
                    """
                )
            )
        except Exception as exc:  # noqa: BLE001
            ui_validation_error = str(exc)

    # ── Structured screenshot directory: screenshots/{Date}/{pass|failed}/{Feature}/ ──
    date_str = datetime.now().strftime("%Y-%m-%d")
    outcome_folder = "pass" if test_outcome == "passed" else "failed"
    feature_folder = _feature_from_nodeid(request.node.nodeid)
    structured_dir = SCREENSHOTS_DIR / date_str / outcome_folder / feature_folder
    structured_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%H%M%S")
    screenshot_path = structured_dir / f"{_SESSION_RUN_ID}_{timestamp_str}.png"
    screenshot_saved = False
    if not page.is_closed():
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            screenshot_saved = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Screenshot capture failed for %s: %s", request.node.nodeid, exc)

    # ── qTest defect — save to pending list for later review ─────────────────
    if test_outcome == "failed" and _QTEST_AVAILABLE:
        qtest_cfg = settings.get("qtest", {}) if isinstance(settings, dict) else {}
        if qtest_cfg.get("enabled", False):
            try:
                import json as _json
                import uuid as _uuid

                error_msg = ""
                stack_trace = ""
                if rep is not None and rep.longrepr:
                    longrepr_str = str(rep.longrepr)
                    error_msg = longrepr_str[:2000]
                    stack_trace = longrepr_str

                pending_entry = {
                    "id": str(_uuid.uuid4()),
                    "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "test_nodeid": request.node.nodeid,
                    "test_file": str(request.node.fspath),
                    "error_message": error_msg or "Test failed (no error message captured)",
                    "stack_trace": stack_trace,
                    "screenshot_path": str(screenshot_path) if screenshot_saved else "",
                    "browser": str(settings.get("browser", "chromium")),
                    "duration_ms": int(duration_ms),
                    "status": "pending",
                }

                _pending_file = Path(__file__).resolve().parent / "reports" / "pending_defects.json"
                _pending_file.parent.mkdir(parents=True, exist_ok=True)

                existing: list[dict] = []
                if _pending_file.exists():
                    try:
                        existing = _json.loads(_pending_file.read_text(encoding="utf-8"))
                    except Exception:
                        existing = []

                existing.append(pending_entry)
                _pending_file.write_text(
                    _json.dumps(existing, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

                logger.info(
                    "qTest defect pending | test=%s | saved to %s | id=%s",
                    request.node.nodeid,
                    _pending_file,
                    pending_entry["id"],
                )
                print(
                    f"\n  [qTest] Failure saved to pending list ({_pending_file.name}).\n"
                    f"  Run  python review_defects.py  from the DocuChat folder to review and log defects.\n"
                )
            except Exception as _qtest_exc:  # noqa: BLE001
                logger.warning(
                    "qTest pending save failed for %s: %s",
                    request.node.nodeid,
                    _qtest_exc,
                )

    failed_count = len(failed_requests)
    server_error_count = len(server_errors)
    avg_network_latency_ms = round(sum(response_latencies_ms) / len(response_latencies_ms), 2) if response_latencies_ms else 0.0

    request.node.user_properties.append(("test_duration_ms", duration_ms))
    request.node.user_properties.append(("avg_network_latency_ms", avg_network_latency_ms))
    request.node.user_properties.append(("network_failed_requests", failed_count))
    request.node.user_properties.append(("network_5xx_responses", server_error_count))
    request.node.user_properties.append(("ui_visible", str(ui_visible)))
    request.node.user_properties.append(("application_version", runtime_validation.get("application_version", "unknown")))
    request.node.user_properties.append(("screenshot_path", str(screenshot_path) if screenshot_saved else ""))

    # Populate rich per-test metadata for auto-summary generation
    # Preserve step_timings if pytest_runtest_logreport already collected them
    _pre_existing = _session_test_metadata.get(request.node.nodeid, {})
    _session_test_metadata[request.node.nodeid] = {
        "status": "PASS" if test_outcome == "passed" else "FAIL",
        "duration_ms": duration_ms,
        "avg_latency_ms": avg_network_latency_ms,
        "failed_requests": failed_count,
        "server_5xx": server_error_count,
        "ui_visible": ui_visible,
        "screenshot": str(screenshot_path) if screenshot_saved else "",
        "error_message": "",
        "observations": [],   # per-test anomaly notes, populated below
        "step_timings": _pre_existing.get("step_timings", []),
    }

    # ── Collect per-test observations for auto-summary ────────────────────
    _obs = _session_test_metadata[request.node.nodeid]["observations"]
    if failed_count > 0:
        _obs.append(f"Network: {failed_count} failed request(s) detected")
    if server_error_count > 0:
        _obs.append(f"Network: {server_error_count} server 5xx response(s)")
    if not ui_visible:
        _obs.append(f"UI visibility validation failed ({ui_validation_error or 'body not visible'})")
    if avg_network_latency_ms > 200:
        _obs.append(f"High network latency: {avg_network_latency_ms:.2f}ms (threshold 200ms)")
    if duration_ms > 120_000:
        _obs.append(f"Long execution: {duration_ms / 1000:.1f}s (threshold 120s)")

    logger.info(
        "Execution checks | test=%s | outcome=%s | duration_ms=%.2f | avg_network_latency_ms=%.2f | "
        "failed_requests=%d | server_5xx=%d | ui_visible=%s | app_version=%s | screenshot=%s",
        request.node.nodeid,
        test_outcome,
        duration_ms,
        avg_network_latency_ms,
        failed_count,
        server_error_count,
        ui_visible,
        runtime_validation.get("application_version", "unknown"),
        str(screenshot_path) if screenshot_saved else "not-captured",
    )

    if failed_requests:
        logger.warning("Network request failures in %s: %s", request.node.nodeid, failed_requests)
    if server_errors:
        logger.warning("Network 5xx responses in %s: %s", request.node.nodeid, server_errors)
    if not ui_visible:
        logger.warning(
            "UI visibility validation failed in %s. error=%s",
            request.node.nodeid,
            ui_validation_error or "body element not visible",
        )

    if strict_network and (failed_count > 0 or server_error_count > 0):
        pytest.fail(
            f"Strict network validation failed for {request.node.nodeid}: "
            f"failed_requests={failed_count}, server_5xx={server_error_count}"
        )
    if strict_ui and not ui_visible:
        pytest.fail(f"Strict UI visibility validation failed for {request.node.nodeid}")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Under xdist, only the controller process should persist aggregated artifacts.
    if hasattr(session.config, "workerinput"):
        return

    terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if not terminal_reporter:
        return

    passed = len(terminal_reporter.stats.get("passed", []))
    failed = len(terminal_reporter.stats.get("failed", []))
    duration_sec = time.time() - float(getattr(session.config, "_execution_start_time", time.time()))

    # Resolve the run artifact label early so all downstream blocks can use it.
    # API enterprise runs get their own label; everything else keeps existing CRT/INT behavior.
    env_tag = getattr(session.config, "option", None)
    runtime_validation = getattr(session.config, "_runtime_validation", None) or {}
    raw_env_label = getattr(env_tag, "environment", None)
    env_label = _resolve_run_artifact_env_label(
        raw_env_label,
        runtime_validation.get("base_url"),
        os.getenv("API_PROFILE"),
        getattr(session, "items", []),
    )

    # ── Persist run history ────────────────────────────────────────────────
    append_run_history(passed=passed, failed=failed, duration_sec=duration_sec)

    # ── Persist per-TC run history for Streamlit dashboard ───────────────
    try:
        _run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tc_results_for_history: dict[str, str] = {}
        for node_id, status in _session_test_results.items():
            func_name = node_id.split("::")[-1]
            tc_match = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
            if tc_match:
                tc_results_for_history[tc_match.group(1).zfill(3)] = status
        if tc_results_for_history:
            append_tc_run_history(
                run_id=_SESSION_RUN_ID,
                tc_results=tc_results_for_history,
                env=env_label,
                run_timestamp=_run_ts,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("TC run history save failed: %s", exc)

    # ── Archive reports snapshot ───────────────────────────────────────────
    try:
        dest = archive_run(tag=env_label)
        prune_old_archives(keep_latest=30)
        logger.info("Reports archived to: %s", dest)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Report archiving failed: %s", exc)

    # ── Auto-update plain-English test case documents ─────────────────────
    try:
        # Group results by feature (chat / file / prompt) based on the test path.
        feature_results: dict[str, dict[str, str]] = {}
        for node_id, status in _session_test_results.items():
            node_path = node_id.split("::")[0].lower().replace("\\", "/")
            for feature_key in _FEATURE_DOC_MAP:
                # Match both "tests/web/chat" (no leading slash, pytest default)
                # and "/tests/web/chat" (leading slash on some platforms).
                if f"tests/web/{feature_key}" in node_path:
                    feature_results.setdefault(feature_key, {})[node_id] = status
                    break

        for feature_key, results in feature_results.items():
            doc_file = TEST_CASE_DOCS_DIR / _FEATURE_DOC_MAP[feature_key]
            feat_total = len(results)
            feat_passed = sum(1 for s in results.values() if s == "PASS")
            feat_failed = feat_total - feat_passed
            _update_test_case_document(
                doc_path=doc_file,
                results=results,
                env=env_label,
                total=feat_total,
                passed=feat_passed,
                failed=feat_failed,
                run_id=_SESSION_RUN_ID,
                run_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Test case document update failed: %s", exc)

    # ── Auto-generate run summary report ──────────────────────────────────
    try:
        # Reconcile metadata with final test outcomes so summary status matches
        # pytest terminal/html outcomes (important for xdist + rerun flows).
        for node_id, status in _session_test_results.items():
            md = _session_test_metadata.setdefault(node_id, {})
            md["status"] = status
            if status == "PASS":
                md["error_message"] = ""
            md.setdefault("duration_ms", 0.0)
            md.setdefault("avg_latency_ms", 0.0)
            md.setdefault("failed_requests", 0)
            md.setdefault("server_5xx", 0)
            md.setdefault("ui_visible", True)
            md.setdefault("screenshot", "")
            md.setdefault("observations", [])
            md.setdefault("step_timings", [])

        if _session_test_metadata:
            # Archive previous summaries before writing new one
            archived = archive_previous_summaries(env_label)
            if archived:
                logger.info("Archived %d previous summary file(s): %s", len(archived), archived)

            summary_path = generate_run_summary(
                env=env_label,
                run_id=_SESSION_RUN_ID,
                run_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                test_results=_session_test_metadata,
                runtime_validation=runtime_validation,
                session_warnings=_session_warnings,
                total_duration_sec=duration_sec,
            )
            logger.info("Run summary generated: %s", summary_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Run summary generation failed: %s", exc)

    # ── Send notifications (Slack / Teams / Email if configured) ──────────
    try:
        send_run_summary(passed=passed, failed=failed, duration_sec=duration_sec, env=env_label)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notification dispatch failed: %s", exc)


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter, exitstatus: int, config: pytest.Config) -> None:
    runtime_validation = getattr(config, "_runtime_validation", None)
    if not runtime_validation:
        return

    status_code = runtime_validation.get('base_url_status', 'unknown')
    status_note = "(expected for authenticated app)" if status_code in (401, 403) else ""

    terminalreporter.write_sep("-", "Runtime Validation")
    terminalreporter.write_line(f"Environment       : {runtime_validation.get('environment', 'unknown')}")
    terminalreporter.write_line(f"Base URL          : {runtime_validation.get('base_url', 'unknown')}")
    terminalreporter.write_line(f"Base URL Status   : {status_code} {status_note}")
    terminalreporter.write_line(f"Base URL Latency  : {runtime_validation.get('base_url_latency_ms', 'unknown')} ms")
    terminalreporter.write_line(f"Application Ver.  : {runtime_validation.get('application_version', 'unknown')}")
    terminalreporter.write_line(f"Python            : {runtime_validation.get('python_version', sys.version.split()[0])}")
    terminalreporter.write_line(f"Playwright        : {runtime_validation.get('playwright_version', 'unknown')}")


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    violations: list[str] = []
    file_pattern = re.compile(r"^test_[a-z0-9_]+\.py$")
    func_pattern = re.compile(r"^test_[a-z0-9_]+$")
    suite_markers = {"smoke", "regression", "sanity"}
    feature_markers = {"chat", "file", "prompt"}

    for item in items:
        file_name = Path(str(item.fspath)).name
        if not file_pattern.match(file_name):
            violations.append(f"Invalid test file name: {file_name}")

        # Use originalname for parametrized tests (strips the [param_id] suffix)
        func_check_name = getattr(item, "originalname", None) or item.name
        if not func_pattern.match(func_check_name):
            violations.append(f"Invalid test function name: {item.name} in {file_name}")

        marker_names = {marker.name for marker in item.iter_markers()}
        suite_present = marker_names.intersection(suite_markers)
        feature_present = marker_names.intersection(feature_markers)
        item_path = Path(str(item.fspath)).as_posix().lower()

        if "/tests/web/" in item_path:
            if len(feature_present) != 1:
                violations.append(
                    f"Web test must have exactly one feature marker (chat/file/prompt): {item.nodeid}"
                )
            if len(suite_present) != 1:
                violations.append(
                    f"Web test must have exactly one suite marker (smoke/regression/sanity): {item.nodeid}"
                )

    if violations:
        details = "\n".join(violations)
        raise pytest.UsageError(
            "Test policy violations detected. "
            "Expected file='test_<feature>_<scenario>.py', function='test_<scenario>', and required markers by test type.\n"
            f"{details}"
        )

