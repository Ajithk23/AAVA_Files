from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from api.client import ApiClient
from api.config import ApiSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_LATEST_RUN_DIR = PROJECT_ROOT / "Test_Latest_Run_Details" / "API-INT_Latest_Run"
API_HISTORY_JSON_PATH = API_LATEST_RUN_DIR / "api_execution_history.json"
API_LATEST_SUMMARY_PATH = API_LATEST_RUN_DIR / "API_Latest_Run_Summary.md"


def _is_api_test_path(file_path: object) -> bool:
    return "/api/" in str(file_path).replace("\\", "/").lower()


@pytest.fixture(scope="session")
def api_settings(pytestconfig: pytest.Config) -> ApiSettings:
    env = pytestconfig.getoption("--env")
    return ApiSettings.from_sources(env=env)


@pytest.fixture(scope="session", autouse=True)
def validate_environment_runtime(
    api_settings: ApiSettings,
    pytestconfig: pytest.Config,
) -> dict[str, object]:
    runtime_validation = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "environment": api_settings.environment,
        "base_url": api_settings.base_url,
        "base_url_status": "not-run",
        "base_url_latency_ms": 0.0,
        "application_version": "api-framework",
        "python_version": "n/a",
        "platform": "n/a",
        "pytest_version": "n/a",
        "playwright_version": "n/a",
    }
    pytestconfig._runtime_validation = runtime_validation
    return runtime_validation


@pytest.fixture(scope="session")
def api_runtime_settings(api_settings: ApiSettings) -> ApiSettings:
    missing = api_settings.missing_required_values()
    if missing:
        pytest.skip(
            "API runtime configuration is incomplete. Missing: " + ", ".join(missing),
            allow_module_level=True,
        )
    return api_settings


@pytest.fixture(scope="session")
def api_client(api_runtime_settings: ApiSettings) -> ApiClient:
    client = ApiClient(api_runtime_settings)
    yield client
    client.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(autouse=True)
def api_test_result_report(
    request: pytest.FixtureRequest,
    api_client: ApiClient,
    api_settings: ApiSettings,
) -> None:
    api_client.clear_history()
    yield

    if not _is_api_test_path(request.node.fspath):
        return

    API_LATEST_RUN_DIR.mkdir(parents=True, exist_ok=True)
    report = getattr(request.node, "rep_call", None)
    status = "PASSED" if report and report.passed else "FAILED"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_function = getattr(request.node, "function", None)
    test_case_name = getattr(test_function, "test_case_name", request.node.name)
    test_case_description = getattr(
        test_function,
        "test_case_description",
        (getattr(test_function, "__doc__", "") or "").strip(),
    )
    safe_name = (
        test_case_name.replace("[", "_")
        .replace("]", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )
    report_path = API_LATEST_RUN_DIR / f"{safe_name}_{timestamp}.md"

    history = api_client.get_history_snapshot()
    lines: list[str] = []
    lines.append(f"# API Execution Result - {test_case_name}")
    lines.append("")
    lines.append(f"- Pytest Test: {request.node.name}")
    if test_case_description:
        lines.append(f"- Description: {test_case_description}")
    lines.append(f"- Timestamp: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Environment: {api_settings.environment}")
    lines.append(f"- Base URL: {api_settings.base_url}")
    lines.append(f"- Result: {status}")
    lines.append("")

    if not history:
        lines.append("No API request history was captured for this test.")
    else:
        for index, entry in enumerate(history, start=1):
            lines.append(f"## Request {index}")
            lines.append("")
            lines.append(f"- Method: {entry['method']}")
            lines.append(f"- URL: {entry['url']}")
            lines.append(f"- Status Code: {entry['status_code']}")
            lines.append(
                f"- Request Headers: `{json.dumps(entry['request_headers'], ensure_ascii=False)}`"
            )
            lines.append(f"- Query Params: `{json.dumps(entry['params'], ensure_ascii=False)}`")
            lines.append("")
            lines.append("### Response Headers")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(entry["response_headers"], indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")
            lines.append("### Complete Response Body")
            lines.append("")
            lines.append("```json")
            lines.append(entry["response_body"])
            lines.append("```")
            lines.append("")

    if report and report.failed and hasattr(report, "longrepr") and report.longrepr:
        lines.append("## Failure Details")
        lines.append("")
        lines.append("```text")
        lines.append(str(report.longrepr))
        lines.append("```")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    history_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "test_case_name": test_case_name,
        "pytest_test_name": request.node.name,
        "description": test_case_description,
        "environment": api_settings.environment,
        "base_url": api_settings.base_url,
        "result": status,
        "report_file": str(report_path),
        "requests": history,
    }

    if report and report.failed and hasattr(report, "longrepr") and report.longrepr:
        history_entry["failure_details"] = str(report.longrepr)

    existing_history: list[dict[str, object]] = []
    if API_HISTORY_JSON_PATH.exists():
        try:
            loaded_history = json.loads(API_HISTORY_JSON_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded_history, list):
                existing_history = loaded_history
        except json.JSONDecodeError:
            existing_history = []

    existing_history.append(history_entry)
    API_HISTORY_JSON_PATH.write_text(
        json.dumps(existing_history, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if hasattr(session.config, "workerinput"):
        return

    terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if not terminal_reporter:
        return

    api_items = [
        item
        for item in getattr(session, "items", [])
        if _is_api_test_path(item.fspath)
    ]
    if not api_items:
        return

    API_LATEST_RUN_DIR.mkdir(parents=True, exist_ok=True)

    skipped = len(terminal_reporter.stats.get("skipped", []))
    deselected = len(terminal_reporter.stats.get("deselected", []))
    xfailed = len(terminal_reporter.stats.get("xfailed", []))
    xpassed = len(terminal_reporter.stats.get("xpassed", []))
    total_duration_sec = time.time() - float(
        getattr(session.config, "_execution_start_time", time.time())
    )

    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    api_settings = ApiSettings.from_sources(env=session.config.getoption("--env"))

    total_collected = len(api_items)
    item_results: list[dict[str, Any]] = []
    for item in api_items:
        call_report = getattr(item, "rep_call", None)
        setup_report = getattr(item, "rep_setup", None)

        if call_report is not None:
            outcome = call_report.outcome
            duration = float(getattr(call_report, "duration", 0.0))
        elif setup_report is not None and setup_report.outcome != "passed":
            outcome = setup_report.outcome
            duration = float(getattr(setup_report, "duration", 0.0))
        else:
            outcome = "deselected"
            duration = 0.0

        item_results.append(
            {
                "nodeid": item.nodeid,
                "outcome": outcome,
                "duration": duration,
            }
        )

    executed_results = [result for result in item_results if result["outcome"] != "deselected"]
    total_executed = len(executed_results)
    total_failed = sum(1 for result in executed_results if result.get("outcome") == "failed")
    total_passed = sum(1 for result in executed_results if result.get("outcome") == "passed")
    total_skipped = sum(1 for result in executed_results if result.get("outcome") == "skipped")
    total_error = sum(1 for result in executed_results if result.get("outcome") == "error")
    pass_rate = round((total_passed / total_executed) * 100, 1) if total_executed else 0.0

    lines: list[str] = []
    lines.append("# API Latest Run Summary")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append(f"- Run Timestamp: {run_timestamp}")
    lines.append(f"- Environment: {api_settings.environment}")
    lines.append(f"- Base URL: {api_settings.base_url}")
    lines.append(f"- Exit Status: {exitstatus}")
    lines.append(f"- Total Duration: {total_duration_sec:.1f}s")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Total API Tests Collected: {total_collected}")
    lines.append(f"- Total API Tests Executed: {total_executed}")
    lines.append(f"- Passed: {total_passed}")
    lines.append(f"- Failed: {total_failed}")
    lines.append(f"- Skipped: {total_skipped}")
    lines.append(f"- Errors: {total_error}")
    lines.append(f"- Deselected: {deselected}")
    lines.append(f"- XFailed: {xfailed}")
    lines.append(f"- XPassed: {xpassed}")
    lines.append(f"- Pass Rate: {pass_rate}%")
    lines.append("")
    lines.append("## Test Results")
    lines.append("")
    lines.append("| Test | Outcome | Duration |")
    lines.append("|---|---|---|")

    for result in sorted(item_results, key=lambda entry: entry["nodeid"]):
        nodeid = result["nodeid"]
        test_name = nodeid.split("::")[-1]
        outcome = str(result.get("outcome", "unknown")).upper()
        duration = float(result.get("duration", 0.0))
        lines.append(f"| `{test_name}` | {outcome} | {duration:.1f}s |")

    if not item_results:
        lines.append("No API test results were captured for this run.")

    lines.append("")
    lines.append(f"*Report auto-generated: {run_timestamp}*")

    summary_content = "\n".join(lines) + "\n"
    timestamped_summary_path = API_LATEST_RUN_DIR / f"API_Run_Summary_{summary_timestamp}.md"
    timestamped_summary_path.write_text(summary_content, encoding="utf-8")
    API_LATEST_SUMMARY_PATH.write_text(summary_content, encoding="utf-8")