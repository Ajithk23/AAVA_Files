"""Auto-generate a run summary report after each pytest session.

The report is written to ``Test_Latest_Run_Details/CRT_QA/`` (default CRT UI automation),
``Test_Latest_Run_Details/INT_QA/`` (when the run targets INT), or
``Test_Latest_Run_Details/ENTERPRISE_QA/`` (when the run targets Enterprise API) and previous
summaries are archived to ``Test_Latest_Run_Details/<folder>/archive/``
before the new one is written.

Works identically whether invoked via:
  - Manual terminal run (``pytest ... --env=int``)
  - CI/CD harness pipeline
  - Scheduled pytest invocation

The module exposes two functions consumed by ``conftest.py``:
  - ``archive_previous_summaries(env)`` — moves existing summaries to archive
  - ``generate_run_summary(env, ...)``  — writes the new summary file
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RUN_DETAILS_DIR = _PROJECT_ROOT / "Test_Latest_Run_Details"

# ── Soft-skip / known-issue markers found in log output ──────────────────
_SOFT_SKIP_PATTERNS: list[tuple[str, str]] = [
    (
        "TC STEP 10 SOFT-SKIP",
        "Step 10 — Character limit NOT enforced by frontend input "
        "(maxlength_attr=-1). Streamlit st.text_input may not have max_chars configured.",
    ),
    (
        "KNOWN ISSUE",
        "Step 13 — Sidebar did not reflect delete within 15 s. "
        "Backend confirmed delete via success banner. Streamlit st.dialog "
        "does not auto-close; sidebar rerender depends on websocket push.",
    ),
    (
        "Copy icon not found",
        "Document Review — Copy icon not found after response. "
        "This chat type may not render the copy element.",
    ),
    (
        "Regenerate Response",
        "Document Review — 'Regenerate Response' button not found. "
        "This chat type may not render the button.",
    ),
    (
        "Soft-skipping",
        "A test step was soft-skipped (non-blocking). "
        "Response was confirmed and test continued.",
    ),
    (
        "Submit button not found",
        "Submit button not found in the UI — Enter key pressed as fallback.",
    ),
]


def _env_folder(env: str) -> Path:
    """Return the QA folder path for the given environment label.

    Supported folders:
    - ``CRT_QA/`` for default CRT-targeted runs
    - ``INT_QA/`` for INT-targeted runs
    - ``ENTERPRISE_QA/`` for Enterprise API-targeted runs

    Any other value is treated as CRT.
    """
    env_lower = env.strip().lower()
    if env_lower == "enterprise":
        folder_name = "ENTERPRISE_QA"
    elif env_lower == "int":
        folder_name = "INT_QA"
    else:
        folder_name = "CRT_QA"
    return _RUN_DETAILS_DIR / folder_name


def archive_previous_summaries(env: str) -> list[str]:
    """Move all existing summary ``.md`` files in ``<ENV>_QA/`` to
    ``<ENV>_QA/archive/``.  Returns a list of archived filenames.
    """
    env_dir = _env_folder(env)
    if not env_dir.exists():
        env_dir.mkdir(parents=True, exist_ok=True)
        return []

    archive_dir = env_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived: list[str] = []
    for md_file in env_dir.glob("*.md"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_name = f"{md_file.stem}_{ts}{md_file.suffix}"
        shutil.move(str(md_file), str(archive_dir / dest_name))
        archived.append(dest_name)

    return archived


def generate_run_summary(
    *,
    env: str,
    run_id: str,
    run_timestamp: str,
    test_results: dict[str, dict[str, Any]],
    runtime_validation: dict[str, Any] | None = None,
    session_warnings: list[str] | None = None,
    total_duration_sec: float = 0.0,
) -> Path:
    """Generate a detailed run summary markdown report.

    Parameters
    ----------
    env : str
        Environment label (``int``, ``crt``, etc.).
    run_id : str
        Unique run identifier (e.g. ``RUN_20260420_154815``).
    run_timestamp : str
        Human-readable timestamp for the run start.
    test_results : dict
        ``{nodeid: {"status": "PASS"|"FAIL", "duration_ms": float,
        "avg_latency_ms": float, "failed_requests": int, ...}}``.
    runtime_validation : dict, optional
        Runtime validation data from conftest (URL, versions, etc.).
    session_warnings : list[str], optional
        Collected warning messages from the session logs.
    total_duration_sec : float
        Total session duration in seconds.

    Returns
    -------
    Path
        The path to the generated summary file.
    """
    env_dir = _env_folder(env)
    env_dir.mkdir(parents=True, exist_ok=True)

    env_upper = env.strip().upper()
    ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Derive test case range from nodeids ───────────────────────────────
    tc_numbers: list[str] = []
    for node_id in test_results:
        func_name = node_id.split("::")[-1]
        tc_match = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
        if tc_match:
            tc_numbers.append(tc_match.group(1).zfill(3))
    tc_numbers.sort()

    if tc_numbers:
        tc_range = f"TC{tc_numbers[0]}_TC{tc_numbers[-1]}"
    else:
        tc_range = "TCs"

    # Derive module from test paths
    modules: set[str] = set()
    for node_id in test_results:
        node_lower = node_id.lower()
        if "/chat/" in node_lower or "\\chat\\" in node_lower:
            modules.add("Chat")
        elif "/file" in node_lower:
            modules.add("File_Management")
        elif "/prompt" in node_lower:
            modules.add("Prompt_Library")
    module_str = "_".join(sorted(modules)) if modules else "Mixed"

    filename = f"{env_upper}_{module_str}_{tc_range}_Run_Summary_{ts_file}.md"
    summary_path = env_dir / filename

    rv = runtime_validation or {}

    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results.values() if r.get("status", "").upper().startswith("PASS"))
    failed_tests = total_tests - passed_tests
    pass_rate = round((passed_tests / total_tests) * 100, 1) if total_tests else 0

    # ── Build markdown ────────────────────────────────────────────────────
    lines: list[str] = []

    lines.append(f"# {env_upper} Environment — {module_str} Module Regression Run Summary")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| **Run ID** | `{run_id}` |")
    lines.append(f"| **Run Timestamp** | {run_timestamp} |")
    lines.append(f"| **Environment** | {env_upper} (`{rv.get('base_url', 'N/A')}`) |")
    lines.append(f"| **Module** | {module_str} |")
    lines.append(f"| **Test Cases Executed** | {tc_range.replace('_', ' – ')} ({total_tests} total) |")
    lines.append(f"| **Total Duration** | {total_duration_sec:.1f}s |")
    lines.append(f"| **Python** | {rv.get('python_version', 'N/A')} |")
    lines.append(f"| **Playwright** | {rv.get('playwright_version', 'N/A')} |")
    lines.append(f"| **pytest** | {rv.get('pytest_version', 'N/A')} |")
    lines.append(f"| **Platform** | {rv.get('platform', 'N/A')} |")
    lines.append(f"| **App Version** | {rv.get('application_version', 'unknown')} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Overall Results ───────────────────────────────────────────────────
    lines.append("## Overall Results")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---|")
    lines.append(f"| **Total Executed** | {total_tests} |")
    lines.append(f"| **Passed** | {passed_tests} |")
    lines.append(f"| **Failed** | {failed_tests} |")
    lines.append(f"| **Pass Rate** | {pass_rate}% |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Detailed Results Table ────────────────────────────────────────────
    lines.append("## Detailed Results")
    lines.append("")
    lines.append("| TC | Test Function | Result | Duration | Avg Latency | Failed Requests |")
    lines.append("|---|---|---|---|---|---|")

    for node_id in sorted(test_results, key=_tc_sort_key):
        info = test_results[node_id]
        func_name = node_id.split("::")[-1]
        tc_match = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
        tc_label = f"TC{tc_match.group(1).zfill(3)}" if tc_match else "—"
        status = info.get("status", "UNKNOWN")
        status_display = f"**PASSED**" if status.upper().startswith("PASS") else f"**FAILED**"

        dur_ms = info.get("duration_ms", 0)
        dur_str = f"{dur_ms / 1000:.1f}s" if dur_ms else "—"

        lat = info.get("avg_latency_ms", 0)
        lat_str = f"{lat:.2f}ms" if lat else "—"

        failed_req = info.get("failed_requests", 0)

        lines.append(f"| {tc_label} | `{func_name}` | {status_display} | {dur_str} | {lat_str} | {failed_req} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Per-Test-Case Step Latency Breakdown (MANDATORY) ──────────────────
    lines.append("## Step-Level Latency Breakdown")
    lines.append("")

    any_steps_found = False
    for node_id in sorted(test_results, key=_tc_sort_key):
        info = test_results[node_id]
        step_timings = info.get("step_timings", [])
        func_name = node_id.split("::")[-1]
        tc_match = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
        tc_label = f"TC{tc_match.group(1).zfill(3)}" if tc_match else func_name

        if step_timings:
            any_steps_found = True
            lines.append(f"### {tc_label}")
            lines.append("")
            lines.append("| Step | Description | Latency | Status |")
            lines.append("|---|---|---|---|")
            for st in sorted(step_timings, key=lambda s: s.get("step", 0)):
                step_num = st.get("step", "?")
                step_name = st.get("name", "—")
                step_lat = st.get("latency_ms", 0)
                step_status = st.get("status", "PASS")
                # Truncate long step names for table readability
                if len(step_name) > 80:
                    step_name = step_name[:77] + "..."
                lat_display = f"{step_lat:.2f}ms" if step_lat < 1000 else f"{step_lat / 1000:.2f}s"
                status_icon = "PASS" if step_status == "PASS" else "**FAIL**"
                lines.append(f"| {step_num} | {step_name} | {lat_display} | {status_icon} |")
            lines.append("")

    if not any_steps_found:
        lines.append("No step-level timing data was captured during this run.")
        lines.append("")

    lines.append("---")
    lines.append("")

    # ── High Latency Report (>5s steps — MANDATORY) ──────────────────────
    _HIGH_LATENCY_THRESHOLD_MS = 5000
    high_latency_rows: list[str] = []

    for node_id in sorted(test_results, key=_tc_sort_key):
        info = test_results[node_id]
        step_timings = info.get("step_timings", [])
        func_name = node_id.split("::")[-1]
        tc_m = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
        tc_lbl = f"TC{tc_m.group(1).zfill(3)}" if tc_m else func_name

        for st in sorted(step_timings, key=lambda s: s.get("step", 0)):
            step_lat = st.get("latency_ms", 0)
            if step_lat >= _HIGH_LATENCY_THRESHOLD_MS:
                step_num = st.get("step", "?")
                step_name = st.get("name", "—")
                if len(step_name) > 80:
                    step_name = step_name[:77] + "..."
                lat_display = f"{step_lat / 1000:.2f}s"
                high_latency_rows.append(
                    f"| {tc_lbl} | {step_num} | {step_name} | {lat_display} |"
                )

    lines.append("## High Latency Report (Steps > 5s)")
    lines.append("")
    if high_latency_rows:
        lines.append(f"**{len(high_latency_rows)} step(s)** exceeded the 5-second threshold.")
        lines.append("")
        lines.append("| TC | Step | Description | Latency |")
        lines.append("|---|---|---|---|")
        for row in high_latency_rows:
            lines.append(row)
    else:
        lines.append("No latency issues detected — all test steps completed within 5 seconds.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Failures Section ──────────────────────────────────────────────────
    failed_entries = {k: v for k, v in test_results.items() if not v.get("status", "").upper().startswith("PASS")}
    if failed_entries:
        lines.append("## Failures")
        lines.append("")
        for node_id, info in sorted(failed_entries.items(), key=lambda x: _tc_sort_key(x[0])):
            func_name = node_id.split("::")[-1]
            tc_match = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
            tc_label = f"TC{tc_match.group(1).zfill(3)}" if tc_match else func_name
            error_msg = info.get("error_message", "No error message captured")
            screenshot = info.get("screenshot", "N/A")

            lines.append(f"### {tc_label} — FAILED")
            lines.append("")
            lines.append(f"- **Test:** `{func_name}`")
            lines.append(f"- **Duration:** {info.get('duration_ms', 0) / 1000:.1f}s")
            lines.append(f"- **Error:** {error_msg}")
            if screenshot and screenshot != "N/A":
                lines.append(f"- **Screenshot:** `{screenshot}`")
            lines.append("")
        lines.append("---")
        lines.append("")

    # ── Soft-Skips / Known Issues (MANDATORY — always shown) ────────────────
    detected_soft_skips: list[str] = []
    if session_warnings:
        for pattern_key, description in _SOFT_SKIP_PATTERNS:
            matching_tcs: list[str] = []
            for w in session_warnings:
                if pattern_key.lower() in w.lower():
                    tc_match = re.search(r"tc(\d+)", w, re.IGNORECASE)
                    if tc_match:
                        tc_label = f"TC{tc_match.group(1).zfill(3)}"
                        if tc_label not in matching_tcs:
                            matching_tcs.append(tc_label)
            if any(pattern_key.lower() in w.lower() for w in session_warnings):
                tcs_str = ", ".join(matching_tcs) if matching_tcs else "Multiple TCs"
                detected_soft_skips.append(f"- **{tcs_str}:** {description}")

    lines.append("## Soft-Skips / Known Issues")
    lines.append("")
    if detected_soft_skips:
        lines.append("The following steps were intentionally soft-skipped during execution. They do not count as failures.")
        lines.append("")
        for skip in detected_soft_skips:
            lines.append(skip)
    else:
        lines.append("No soft-skips or known issues were detected during this run.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Unusual Application Behavior (MANDATORY — always shown) ───────────
    unusual_behaviors: list[str] = []

    # Surface per-TC observations (network anomalies, UI issues, long runs)
    for node_id in sorted(test_results, key=_tc_sort_key):
        info = test_results[node_id]
        observations = info.get("observations", [])
        if observations:
            func_name = node_id.split("::")[-1]
            tc_m = re.search(r"tc(\d+)", func_name, re.IGNORECASE)
            tc_lbl = f"TC{tc_m.group(1).zfill(3)}" if tc_m else func_name
            for obs in observations:
                unusual_behaviors.append(f"- **{tc_lbl}:** {obs}")

    # Surface aggregate network / UI anomalies
    total_5xx = sum(r.get("server_5xx", 0) for r in test_results.values())
    total_failed_req = sum(r.get("failed_requests", 0) for r in test_results.values())
    ui_fail_count = sum(1 for r in test_results.values() if not r.get("ui_visible", True))
    if total_5xx > 0:
        unusual_behaviors.append(f"- **Session total:** {total_5xx} server 5xx response(s) across all tests")
    if total_failed_req > 0:
        unusual_behaviors.append(f"- **Session total:** {total_failed_req} failed network request(s) across all tests")
    if ui_fail_count > 0:
        unusual_behaviors.append(f"- **Session total:** {ui_fail_count} test(s) had UI visibility validation failures")

    lines.append("## Unusual Application Behavior")
    lines.append("")
    if unusual_behaviors:
        for behavior in unusual_behaviors:
            lines.append(behavior)
    else:
        lines.append("No unusual application behavior was observed during this run.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Other Session Warnings (MANDATORY — always shown) ─────────────────
    other_warnings: list[str] = []
    if session_warnings:
        skip_patterns_lower = [p[0].lower() for p in _SOFT_SKIP_PATTERNS]
        for w in session_warnings:
            w_lower = w.lower()
            if not any(sp in w_lower for sp in skip_patterns_lower):
                if w not in other_warnings:
                    other_warnings.append(w)

    lines.append("## Other Warnings")
    lines.append("")
    if other_warnings:
        for w in other_warnings:
            lines.append(f"- {w}")
    else:
        lines.append("No additional warnings were recorded during this run.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Environment Observations (MANDATORY — always shown) ───────────────
    lines.append("## Environment Observations")
    lines.append("")
    app_ver = rv.get("application_version", "unknown")
    lines.append(f"- **App Version:** {app_ver}")
    if app_ver in ("unknown", "N/A", ""):
        lines.append("  - The application did not expose a version number via the expected mechanism.")
    base_url = rv.get("base_url", "N/A")
    base_status = rv.get("base_url_status", "N/A")
    base_latency = rv.get("base_url_latency_ms", "N/A")
    lines.append(f"- **Base URL:** {base_url} (status: {base_status}, latency: {base_latency}ms)")
    lines.append(f"- **Platform:** {rv.get('platform', 'N/A')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Footer ────────────────────────────────────────────────────────────
    lines.append(f"*Report auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def _tc_sort_key(node_id: str) -> tuple[int, str]:
    """Sort key that extracts TC number for ordering."""
    func = node_id.split("::")[-1] if "::" in node_id else node_id
    tc_match = re.search(r"tc(\d+)", func, re.IGNORECASE)
    if tc_match:
        return (int(tc_match.group(1)), func)
    return (9999, func)
