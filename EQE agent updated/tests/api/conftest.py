from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

from api.client import ApiClient
from api.config import ApiSettings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalize_report_profile(profile: str | None) -> str:
    normalized = (profile or "default").strip().lower()
    return normalized or "default"


def _infer_report_profile(node_path: str, fallback_profile: str | None = None) -> str:
    normalized_path = node_path.replace("\\", "/").lower()
    if "/tests/api/enterprise_api_testcases/" in normalized_path:
        return "enterprise"
    return _normalize_report_profile(fallback_profile)


def _api_result_folder_name(profile: str | None) -> str:
    if _normalize_report_profile(profile) == "enterprise":
        return "API-ENTERPRISE_Latest_Run"
    return "API-INT_Latest_Run"


def _api_result_paths(api_settings: ApiSettings, profile_override: str | None = None) -> tuple[Path, Path, Path]:
    profile = profile_override or api_settings.profile
    latest_run_dir = PROJECT_ROOT / "Test_Latest_Run_Details" / _api_result_folder_name(profile)
    history_json_path = latest_run_dir / "api_execution_history.json"
    latest_summary_path = latest_run_dir / "API_Latest_Run_Summary.md"
    return latest_run_dir, history_json_path, latest_summary_path


def _collect_api_clients(request: pytest.FixtureRequest, fallback_client: ApiClient) -> list[tuple[str, ApiClient]]:
    clients: list[tuple[str, ApiClient]] = []
    seen_ids: set[int] = set()

    for fixture_name in request.fixturenames:
        if "api_client" not in fixture_name:
            continue
        fixture_value = request.getfixturevalue(fixture_name)
        if isinstance(fixture_value, ApiClient) and id(fixture_value) not in seen_ids:
            clients.append((fixture_name, fixture_value))
            seen_ids.add(id(fixture_value))

    if id(fallback_client) not in seen_ids:
        clients.append(("api_client", fallback_client))

    return clients


def _resolve_report_client(request: pytest.FixtureRequest, fallback_client: ApiClient) -> ApiClient:
    clients = _collect_api_clients(request, fallback_client)
    for fixture_name, client in clients:
        if fixture_name != "api_client":
            return client
    return fallback_client


def _resolve_report_settings(request: pytest.FixtureRequest, fallback_settings: ApiSettings) -> ApiSettings:
    for fixture_name in request.fixturenames:
        if "settings" not in fixture_name:
            continue
        fixture_value = request.getfixturevalue(fixture_name)
        if isinstance(fixture_value, ApiSettings) and fixture_name != "api_settings":
            return fixture_value
    return fallback_settings


def _load_history_entries(history_json_path: Path) -> list[dict[str, Any]]:
    if not history_json_path.exists():
        return []

    try:
        loaded_history = json.loads(history_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(loaded_history, list):
        return []

    return [entry for entry in loaded_history if isinstance(entry, dict)]


def _resolve_test_case_metadata(request: pytest.FixtureRequest) -> tuple[str, str]:
    test_function = getattr(request.node, "function", None)
    explicit_name = getattr(test_function, "test_case_name", "")
    explicit_description = getattr(test_function, "test_case_description", "")
    callspec = getattr(request.node, "callspec", None)
    runtime_case_id = getattr(callspec, "id", "") if callspec is not None else ""
    docstring = (getattr(test_function, "__doc__", "") or "").strip()

    test_case_name = explicit_name or runtime_case_id or request.node.name
    test_case_description = explicit_description or docstring
    return test_case_name, test_case_description


def _format_request_paths(history_entry: dict[str, Any]) -> str:
    requests = history_entry.get("requests", [])
    if not isinstance(requests, list) or not requests:
        return "N/A"

    formatted_paths: list[str] = []
    for request in requests:
        if not isinstance(request, dict):
            continue
        method = str(request.get("method", "")).upper().strip()
        url = str(request.get("url", "")).strip()
        path = urlparse(url).path if url else ""
        path = re.sub(r"/response/resp_[^/]+/?$", "/response/{response_id}/", path)
        path = re.sub(r"/responses/resp_[^/]+/?$", "/responses/{response_id}/", path)
        formatted = " ".join(part for part in [method, path] if part)
        if formatted and formatted not in formatted_paths:
            formatted_paths.append(formatted)

    return "<br>".join(formatted_paths) if formatted_paths else "N/A"


def _format_status_codes(history_entry: dict[str, Any]) -> str:
    requests = history_entry.get("requests", [])
    if not isinstance(requests, list) or not requests:
        return "N/A"

    codes: list[str] = []
    for request in requests:
        if not isinstance(request, dict):
            continue
        status_code = request.get("status_code")
        if status_code is None:
            continue
        code = str(status_code)
        if code not in codes:
            codes.append(code)

    return ", ".join(codes) if codes else "N/A"


def _normalize_report_base_url(profile: str, base_url: str) -> str:
    if profile == "enterprise" and "/enterprise/docs/" in base_url:
        return base_url.split("/enterprise/docs/", 1)[0].rstrip("/")
    return base_url.rstrip("/")


def _extract_tc_group(test_case_name: str) -> str:
    match = re.match(r"^(TC\d+)", test_case_name.strip(), flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return test_case_name.strip() or "UNKNOWN"


def _should_include_history_entry(profile: str, history_entry: dict[str, Any]) -> bool:
    test_case_name = str(history_entry.get("test_case_name", "")).strip()
    pytest_test_name = str(history_entry.get("pytest_test_name", "")).strip().lower()
    report_file = str(history_entry.get("report_file", "")).replace("\\", "/").lower()

    if profile == "enterprise":
        return bool(re.match(r"^TC\d+", test_case_name, flags=re.IGNORECASE)) or "enterprise_ai" in pytest_test_name or "enterprise_ai" in report_file
    return True


def _aggregate_latest_rows(profile: str, history_entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    filtered_entries = [
        entry for entry in history_entries if _should_include_history_entry(profile, entry)
    ]

    latest_by_group: dict[str, dict[str, Any]] = {}
    for entry in sorted(
        filtered_entries,
        key=lambda item: str(item.get("timestamp", "")),
        reverse=True,
    ):
        test_case_name = str(entry.get("test_case_name", "N/A"))
        group_key = _extract_tc_group(test_case_name)
        if group_key not in latest_by_group:
            latest_by_group[group_key] = entry

    rows: list[dict[str, str]] = []
    for group_key in sorted(latest_by_group.keys()):
        entry = latest_by_group[group_key]
        description = str(entry.get("description", "") or "N/A").replace("\n", " ").strip()
        rows.append(
            {
                "timestamp": str(entry.get("timestamp", "N/A")),
                "tc_name": group_key,
                "description": description or "N/A",
                "endpoint": _format_request_paths(entry),
                "response_code": _format_status_codes(entry),
                "result": str(entry.get("result", "UNKNOWN")).upper(),
            }
        )

    return rows


def _aggregate_latest_item_results(profile: str, history_entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    filtered_entries = [
        entry for entry in history_entries if _should_include_history_entry(profile, entry)
    ]

    latest_by_item: dict[str, dict[str, Any]] = {}
    for entry in sorted(
        filtered_entries,
        key=lambda item: str(item.get("timestamp", "")),
        reverse=True,
    ):
        item_key = str(entry.get("test_case_name", "N/A")).strip() or str(entry.get("pytest_test_name", "N/A")).strip()
        if item_key not in latest_by_item:
            latest_by_item[item_key] = entry

    item_results: list[dict[str, str]] = []
    for item_key in sorted(latest_by_item.keys()):
        entry = latest_by_item[item_key]
        item_results.append(
            {
                "item_name": item_key,
                "result": str(entry.get("result", "UNKNOWN")).upper(),
            }
        )

    return item_results


def _build_failed_rows(latest_rows: list[dict[str, str]], history_entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    failure_details_by_tc: dict[str, str] = {}
    for entry in sorted(
        history_entries,
        key=lambda item: str(item.get("timestamp", "")),
        reverse=True,
    ):
        test_case_name = str(entry.get("test_case_name", "N/A"))
        tc_name = _extract_tc_group(test_case_name)
        if tc_name in failure_details_by_tc:
            continue
        if str(entry.get("result", "")).upper() != "FAILED":
            continue

        failure_reason = str(entry.get("failure_details", "") or "No failure details captured.").strip()
        failure_details_by_tc[tc_name] = failure_reason

    failed_rows: list[dict[str, str]] = []
    for row in latest_rows:
        if row.get("result") != "FAILED":
            continue
        failed_rows.append(
            {
                "tc_name": row["tc_name"],
                "description": row["description"],
                "endpoint": row["endpoint"].replace("<br>", ", "),
                "response_code": row["response_code"],
                "reason": failure_details_by_tc.get(row["tc_name"], "No failure details captured."),
            }
        )

    return failed_rows


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
    clients = _collect_api_clients(request, api_client)
    for _, client in clients:
        client.clear_history()

    yield

    node_path = str(request.node.fspath)
    if "/tests/api/" not in node_path.replace("\\", "/").lower():
        return

    report_settings = _resolve_report_settings(request, api_settings)
    report_client = _resolve_report_client(request, api_client)
    report_profile = _infer_report_profile(node_path, report_settings.profile)
    latest_run_dir, history_json_path, _ = _api_result_paths(
        report_settings,
        profile_override=report_profile,
    )
    latest_run_dir.mkdir(parents=True, exist_ok=True)

    report = getattr(request.node, "rep_call", None)
    status = "PASSED" if report and report.passed else "FAILED"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_case_name, test_case_description = _resolve_test_case_metadata(request)
    safe_name = test_case_name.replace("[", "_").replace("]", "_").replace("/", "_").replace("\\", "_")
    report_path = latest_run_dir / f"{safe_name}_{timestamp}.md"

    history = report_client.get_history_snapshot()
    lines: list[str] = []
    lines.append(f"# API Execution Result - {test_case_name}")
    lines.append("")
    lines.append(f"- Pytest Test: {request.node.name}")
    if test_case_description:
        lines.append(f"- Description: {test_case_description}")
    lines.append(f"- Timestamp: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Environment: {report_settings.environment}")
    lines.append(f"- Base URL: {report_settings.base_url}")
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
            lines.append(f"- Request Headers: `{json.dumps(entry['request_headers'], ensure_ascii=False)}`")
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

    history_entry: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "test_case_name": test_case_name,
        "pytest_test_name": request.node.name,
        "description": test_case_description,
        "environment": report_settings.environment,
        "base_url": report_settings.base_url,
        "result": status,
        "report_file": str(report_path),
        "requests": history,
    }

    if report and report.failed and hasattr(report, "longrepr") and report.longrepr:
        history_entry["failure_details"] = str(report.longrepr)

    existing_history = _load_history_entries(history_json_path)
    existing_history.append(history_entry)
    history_json_path.write_text(
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
        if "/tests/api/" in str(item.fspath).replace("\\", "/").lower()
    ]
    if not api_items:
        return

    total_duration_sec = time.time() - float(
        getattr(session.config, "_execution_start_time", time.time())
    )
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    env = session.config.getoption("--env")

    profile_groups: dict[str, list[pytest.Item]] = {}
    for item in api_items:
        profile = _infer_report_profile(str(item.fspath))
        profile_groups.setdefault(profile, []).append(item)

    for profile, profile_items in profile_groups.items():
        profile_settings = ApiSettings.from_sources(
            env=env,
            profile=None if profile == "default" else profile,
        )
        latest_run_dir, history_json_path, latest_summary_path = _api_result_paths(
            profile_settings,
            profile_override=profile,
        )
        latest_run_dir.mkdir(parents=True, exist_ok=True)
        item_results: list[dict[str, Any]] = []
        for item in profile_items:
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

        latest_history = _load_history_entries(history_json_path)
        latest_rows = _aggregate_latest_rows(profile, latest_history)
        failed_rows = _build_failed_rows(latest_rows, latest_history)
        total_collected = len(latest_rows)
        total_executed = len(latest_rows)
        latest_item_results = _aggregate_latest_item_results(profile, latest_history)
        executed_test_items_count = len(latest_item_results)
        passed_test_items_count = sum(1 for item in latest_item_results if item.get("result") == "PASSED")
        failed_test_items_count = sum(1 for item in latest_item_results if item.get("result") == "FAILED")
        skipped_test_items_count = sum(1 for item in latest_item_results if item.get("result") == "SKIPPED")
        errored_test_items_count = sum(1 for item in latest_item_results if item.get("result") == "ERROR")
        total_passed = sum(1 for row in latest_rows if row.get("result") == "PASSED")
        total_failed = sum(1 for row in latest_rows if row.get("result") == "FAILED")
        total_skipped = sum(1 for row in latest_rows if row.get("result") == "SKIPPED")
        total_error = sum(1 for row in latest_rows if row.get("result") == "ERROR")
        total_deselected = 0
        pass_rate = round((total_passed / total_executed) * 100, 1) if total_executed else 0.0
        base_url = _normalize_report_base_url(profile, profile_settings.base_url)

        lines: list[str] = []
        lines.append("# API Latest Run Summary")
        lines.append("")
        lines.append("## Run Metadata")
        lines.append("")
        lines.append(f"- Run Timestamp: {run_timestamp}")
        lines.append(f"- Environment: {profile_settings.environment}")
        lines.append(f"- API Profile: {profile}")
        lines.append(f"- Base URL: {base_url}")
        lines.append(f"- Exit Status: {exitstatus}")
        lines.append(f"- Total Duration: {total_duration_sec:.1f}s")
        lines.append("")
        lines.append("## Counts")
        lines.append("")
        lines.append(f"- Total API Test Cases: {total_collected}")
        lines.append(f"- Total API Test Cases Executed: {total_executed}")
        lines.append(f"- Executed Test Items Count: {executed_test_items_count}")
        lines.append(f"- Passed Test Items Count: {passed_test_items_count}")
        lines.append(f"- Failed Test Items Count: {failed_test_items_count}")
        lines.append(f"- Skipped Test Items Count: {skipped_test_items_count}")
        lines.append(f"- Errored Test Items Count: {errored_test_items_count}")
        lines.append(f"- Passed: {total_passed}")
        lines.append(f"- Failed: {total_failed}")
        lines.append(f"- Skipped: {total_skipped}")
        lines.append(f"- Errors: {total_error}")
        lines.append(f"- Deselected: {total_deselected}")
        lines.append("- XFailed: 0")
        lines.append("- XPassed: 0")
        lines.append(f"- Pass Rate: {pass_rate}%")

        if failed_rows:
            lines.append("")
            lines.append("## Failed Test Cases")
            lines.append("")
            for failed_row in failed_rows:
                lines.append(f"- TC_Name: {failed_row['tc_name']}")
                lines.append(f"- Test case description: {failed_row['description']}")
                lines.append(f"- Endpoint: {failed_row['endpoint']}")
                lines.append(f"- Response code: {failed_row['response_code']}")
                lines.append(f"- Failure reason: {failed_row['reason']}")
                lines.append("")

        summary_content = "\n".join(lines) + "\n"
        timestamped_summary_path = latest_run_dir / f"API_Run_Summary_{summary_timestamp}.md"
        timestamped_summary_path.write_text(summary_content, encoding="utf-8")
        latest_summary_path.write_text(summary_content, encoding="utf-8")