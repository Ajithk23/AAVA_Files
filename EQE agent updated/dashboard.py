from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_ROOT / "reports"
HISTORY_FILE = REPORTS_DIR / "history" / "run_history.json"
TC_HISTORY_FILE = REPORTS_DIR / "history" / "tc_run_history.json"
ARCHIVE_DIR = REPORTS_DIR / "archive"
LATEST_HTML = REPORTS_DIR / "latest_report.html"
LIVE_ALLURE_DIR = REPORTS_DIR / "allure-results"
LIVE_SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"


def _is_running_in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def _launch_via_streamlit() -> int:
    command = [
        sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
        "--server.port=8501",
        "--server.headless=true",
        "--server.runOnSave=false",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]
    return subprocess.call(command, cwd=PROJECT_ROOT)


def _ensure_required_folders() -> None:
    (REPORTS_DIR / "dashboard").mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "history").mkdir(parents=True, exist_ok=True)


def _safe_json_load(file_path: Path) -> Any:
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _run_meta_from_archive_folder(folder: Path) -> dict[str, Any]:
    folder_name = folder.name
    parts = folder_name.split("_")

    run_timestamp: datetime | None = None
    env = "unknown"
    run_id = f"RUN_{folder_name}"

    if len(parts) >= 2:
        stamp_candidate = f"{parts[0]}_{parts[1]}"
        try:
            run_timestamp = datetime.strptime(stamp_candidate, "%Y%m%d_%H%M%S")
            run_id = f"RUN_{run_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"
            if len(parts) >= 3:
                env = parts[-1].lower()
        except ValueError:
            run_timestamp = None

    return {
        "RunID": run_id,
        "Environment": env,
        "RunFolder": str(folder),
        "Timestamp": run_timestamp,
        "TimestampText": _fmt_dt(run_timestamp),
    }


def _labels_to_map(labels: list[dict[str, Any]]) -> dict[str, list[str]]:
    label_map: dict[str, list[str]] = {}
    for label in labels:
        name = str(label.get("name", "")).strip()
        value = str(label.get("value", "")).strip()
        if not name or not value:
            continue
        label_map.setdefault(name, []).append(value)
    return label_map


def _derive_feature(tags: list[str], parent_suite: str, full_name: str) -> str:
    joined = " ".join([*tags, parent_suite, full_name]).lower()
    if "chat" in joined:
        return "Chat"
    if "file" in joined:
        return "File Management"
    if "prompt" in joined:
        return "Prompt Library"
    return "Unknown"


def _derive_test_type(tags: list[str], full_name: str) -> str:
    lowered_tags = {tag.lower() for tag in tags}
    if "smoke" in lowered_tags:
        return "Smoke"
    if "regression" in lowered_tags:
        return "Regression"
    if "functional" in lowered_tags:
        return "Functional"
    if "sanity" in lowered_tags:
        return "Sanity"
    if "regression" in full_name.lower():
        return "Regression"
    return "Unknown"


def _normalize_status(raw_status: str) -> str:
    status = (raw_status or "").strip().lower()
    if status == "passed":
        return "Pass"
    if status in {"failed", "broken"}:
        return "Fail"
    if status == "skipped":
        return "Skip"
    return status.title() if status else "Unknown"


def _resolve_screenshot_path(result_data: dict[str, Any], run_folder: Path, test_case: str) -> str:
    attachments = result_data.get("attachments", [])
    if isinstance(attachments, list):
        for attachment in attachments:
            source_name = str(attachment.get("source", "")).strip()
            if not source_name:
                continue
            run_attachment = run_folder / "allure-results" / source_name
            if run_attachment.exists():
                return str(run_attachment)

    screenshots_dir = run_folder / "screenshots"
    if screenshots_dir.exists():
        for png in screenshots_dir.rglob("*.png"):
            if test_case.lower() in png.name.lower():
                return str(png)

    if LIVE_SCREENSHOTS_DIR.exists():
        for png in LIVE_SCREENSHOTS_DIR.glob("*.png"):
            if test_case.lower() in png.name.lower():
                return str(png)

    return ""


def _parse_allure_results_in_folder(run_folder: Path) -> list[dict[str, Any]]:
    meta = _run_meta_from_archive_folder(run_folder)
    allure_dir = run_folder / "allure-results"
    if not allure_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for result_file in allure_dir.glob("*-result.json"):
        result_data = _safe_json_load(result_file)
        if not isinstance(result_data, dict):
            continue

        labels = result_data.get("labels", [])
        label_map = _labels_to_map(labels if isinstance(labels, list) else [])
        tags = [value for value in label_map.get("tag", [])]
        parent_suite = (label_map.get("parentSuite") or [""])[0]
        host_value = (label_map.get("host") or [""])[0]
        test_case = str(result_data.get("name", "")).strip() or "unknown_test"
        full_name = str(result_data.get("fullName", "")).strip()

        start_epoch = result_data.get("start")
        stop_epoch = result_data.get("stop")

        start_time: datetime | None = None
        end_time: datetime | None = None
        if isinstance(start_epoch, (int, float)):
            start_time = datetime.fromtimestamp(float(start_epoch) / 1000)
        if isinstance(stop_epoch, (int, float)):
            end_time = datetime.fromtimestamp(float(stop_epoch) / 1000)

        event_time = meta["Timestamp"] or start_time or end_time
        duration_sec = ""
        if start_time and end_time:
            duration_sec = round((end_time - start_time).total_seconds(), 2)

        status = _normalize_status(str(result_data.get("status", "")))
        screenshot_path = _resolve_screenshot_path(result_data, run_folder=run_folder, test_case=test_case)

        records.append(
            {
                "RunID": meta["RunID"],
                "Environment": str(meta["Environment"]).upper(),
                "User": host_value or "Unknown",
                "TestCase": test_case,
                "Feature": _derive_feature(tags=tags, parent_suite=parent_suite, full_name=full_name),
                "TestType": _derive_test_type(tags=tags, full_name=full_name),
                "Status": status,
                "StartTime": _fmt_dt(start_time),
                "EndTime": _fmt_dt(end_time),
                "Timestamp": _fmt_dt(event_time),
                "TimestampObj": event_time,
                "DurationSec": duration_sec,
                "ScreenshotPath": screenshot_path,
                "ResultFile": str(result_file),
                "FullName": full_name,
            }
        )

    return records


def _load_all_test_records() -> pd.DataFrame:
    archive_records: list[dict[str, Any]] = []
    if ARCHIVE_DIR.exists():
        for run_folder in sorted([path for path in ARCHIVE_DIR.iterdir() if path.is_dir()]):
            archive_records.extend(_parse_allure_results_in_folder(run_folder))

    if not archive_records and LIVE_ALLURE_DIR.exists():
        pseudo_folder = REPORTS_DIR / "_live"
        pseudo_folder.mkdir(exist_ok=True)
        temp_allure_dir = pseudo_folder / "allure-results"
        temp_allure_dir.mkdir(exist_ok=True)
        for file in LIVE_ALLURE_DIR.glob("*-result.json"):
            data = _safe_json_load(file)
            if not isinstance(data, dict):
                continue
            labels = data.get("labels", [])
            label_map = _labels_to_map(labels if isinstance(labels, list) else [])
            tags = [value for value in label_map.get("tag", [])]
            full_name = str(data.get("fullName", ""))
            status = _normalize_status(str(data.get("status", "")))
            test_case = str(data.get("name", "")).strip() or "unknown_test"
            start_epoch = data.get("start")
            stop_epoch = data.get("stop")
            start_time = datetime.fromtimestamp(float(start_epoch) / 1000) if isinstance(start_epoch, (int, float)) else None
            end_time = datetime.fromtimestamp(float(stop_epoch) / 1000) if isinstance(stop_epoch, (int, float)) else None
            archive_records.append(
                {
                    "RunID": "RUN_LIVE",
                    "Environment": "UNKNOWN",
                    "User": (label_map.get("host") or ["Unknown"])[0],
                    "TestCase": test_case,
                    "Feature": _derive_feature(tags=tags, parent_suite=(label_map.get("parentSuite") or [""])[0], full_name=full_name),
                    "TestType": _derive_test_type(tags=tags, full_name=full_name),
                    "Status": status,
                    "StartTime": _fmt_dt(start_time),
                    "EndTime": _fmt_dt(end_time),
                    "Timestamp": _fmt_dt(start_time or end_time),
                    "TimestampObj": start_time or end_time,
                    "DurationSec": round((end_time - start_time).total_seconds(), 2) if start_time and end_time else "",
                    "ScreenshotPath": "",
                    "ResultFile": str(file),
                    "FullName": full_name,
                }
            )

    if not archive_records:
        return pd.DataFrame(
            columns=[
                "RunID",
                "Environment",
                "User",
                "TestCase",
                "Feature",
                "TestType",
                "Status",
                "StartTime",
                "EndTime",
                "Timestamp",
                "TimestampObj",
                "DurationSec",
                "ScreenshotPath",
                "ResultFile",
                "FullName",
            ]
        )

    dataframe = pd.DataFrame(archive_records)
    dataframe["TimestampObj"] = pd.to_datetime(dataframe["TimestampObj"], errors="coerce")
    # Archived allure-results can contain carry-over duplicates from earlier runs.
    # Keep only the latest record per RunID + test case to represent one execution per test case per run.
    dataframe["_dedup_key"] = dataframe["FullName"].fillna("").astype(str)
    dataframe.loc[dataframe["_dedup_key"].str.len() == 0, "_dedup_key"] = dataframe["TestCase"].fillna("").astype(str)
    dataframe = dataframe.sort_values(by=["RunID", "_dedup_key", "TimestampObj"], na_position="last")
    dataframe = dataframe.drop_duplicates(subset=["RunID", "_dedup_key"], keep="last")
    dataframe = dataframe.drop(columns=["_dedup_key"])
    return dataframe


def _load_run_history() -> pd.DataFrame:
    payload = _safe_json_load(HISTORY_FILE)
    if not isinstance(payload, list):
        return pd.DataFrame(columns=["run_count", "passed", "failed", "duration_sec", "timestamp"])

    dataframe = pd.DataFrame(payload)
    if dataframe.empty:
        return dataframe

    if "timestamp" in dataframe.columns:
        dataframe["timestamp_obj"] = pd.to_datetime(dataframe["timestamp"], errors="coerce")
    else:
        dataframe["timestamp_obj"] = pd.NaT

    if "pass_percent" not in dataframe.columns:
        passed = pd.to_numeric(dataframe.get("passed", 0), errors="coerce").fillna(0)
        failed = pd.to_numeric(dataframe.get("failed", 0), errors="coerce").fillna(0)
        total = passed + failed
        dataframe["pass_percent"] = ((passed / total.where(total != 0, 1)) * 100).round(2)

    return dataframe


def _apply_filters(
    tests_df: pd.DataFrame,
    runs_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    st.sidebar.header("Filters")

    candidate_dates: list[date] = []
    if not tests_df.empty:
        candidate_dates.extend([value.date() for value in tests_df["TimestampObj"].dropna().tolist()])
    if not runs_df.empty and "timestamp_obj" in runs_df.columns:
        candidate_dates.extend([value.date() for value in runs_df["timestamp_obj"].dropna().tolist()])

    today = date.today()
    min_date = min(candidate_dates) if candidate_dates else today
    max_date = max(candidate_dates) if candidate_dates else today

    selected_date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date))
    if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
        start_date, end_date = selected_date_range
    else:
        start_date, end_date = min_date, max_date

    start_time = st.sidebar.time_input("Start Time", value=time(0, 0))
    end_time = st.sidebar.time_input("End Time", value=time(23, 59, 59))

    start_dt = datetime.combine(start_date, start_time)
    end_dt = datetime.combine(end_date, end_time)

    feature_options = sorted([value for value in tests_df.get("Feature", pd.Series(dtype=str)).dropna().unique().tolist() if value])
    test_type_options = sorted([value for value in tests_df.get("TestType", pd.Series(dtype=str)).dropna().unique().tolist() if value])
    status_options = sorted([value for value in tests_df.get("Status", pd.Series(dtype=str)).dropna().unique().tolist() if value])
    env_options = sorted([value for value in tests_df.get("Environment", pd.Series(dtype=str)).dropna().unique().tolist() if value])
    run_id_options = sorted([value for value in tests_df.get("RunID", pd.Series(dtype=str)).dropna().unique().tolist() if value])
    user_options = sorted([value for value in tests_df.get("User", pd.Series(dtype=str)).dropna().unique().tolist() if value])

    selected_features = st.sidebar.multiselect("Feature", options=feature_options, default=feature_options)
    selected_test_types = st.sidebar.multiselect("Test Type", options=test_type_options, default=test_type_options)
    selected_statuses = st.sidebar.multiselect("Status", options=status_options, default=status_options)
    selected_envs = st.sidebar.multiselect("Environment", options=env_options, default=env_options)
    selected_run_ids = st.sidebar.multiselect("RunID", options=run_id_options, default=run_id_options)
    selected_users = st.sidebar.multiselect("User", options=user_options, default=user_options)

    filtered_tests = tests_df.copy()
    if not filtered_tests.empty:
        # Include records with no timestamp (NaT) so they always appear, plus timestamped records in range
        filtered_tests = filtered_tests[
            filtered_tests["TimestampObj"].isna()
            | (
                (filtered_tests["TimestampObj"] >= pd.Timestamp(start_dt))
                & (filtered_tests["TimestampObj"] <= pd.Timestamp(end_dt))
            )
        ]
        if selected_features:
            filtered_tests = filtered_tests[filtered_tests["Feature"].isin(selected_features)]
        if selected_test_types:
            filtered_tests = filtered_tests[filtered_tests["TestType"].isin(selected_test_types)]
        if selected_statuses:
            filtered_tests = filtered_tests[filtered_tests["Status"].isin(selected_statuses)]
        if selected_envs:
            filtered_tests = filtered_tests[filtered_tests["Environment"].isin(selected_envs)]
        if selected_run_ids:
            filtered_tests = filtered_tests[filtered_tests["RunID"].isin(selected_run_ids)]
        if selected_users:
            filtered_tests = filtered_tests[filtered_tests["User"].isin(selected_users)]

    filtered_runs = runs_df.copy()
    if not filtered_runs.empty and "timestamp_obj" in filtered_runs.columns:
        filtered_runs = filtered_runs[
            filtered_runs["timestamp_obj"].notna()
            & (filtered_runs["timestamp_obj"] >= pd.Timestamp(start_dt))
            & (filtered_runs["timestamp_obj"] <= pd.Timestamp(end_dt))
        ]

    return filtered_tests, filtered_runs


def _render_summary_cards(filtered_tests: pd.DataFrame, filtered_runs: pd.DataFrame, all_tests_df: pd.DataFrame) -> None:
    # Total Tests = unique test case names across the entire dataset (not affected by date filter)
    total_tests = int(all_tests_df["TestCase"].nunique()) if not all_tests_df.empty else 0
    # Executions = total individual test runs in the filtered view (each row = 1 execution)
    total_executions = int(len(filtered_tests)) if not filtered_tests.empty else 0

    if not filtered_tests.empty:
        passed_count = int((filtered_tests["Status"] == "Pass").sum())
        failed_count = int((filtered_tests["Status"] == "Fail").sum())
    elif not filtered_runs.empty:
        passed_count = int(pd.to_numeric(filtered_runs.get("passed", 0), errors="coerce").fillna(0).sum())
        failed_count = int(pd.to_numeric(filtered_runs.get("failed", 0), errors="coerce").fillna(0).sum())
    else:
        passed_count = 0
        failed_count = 0

    denominator = passed_count + failed_count
    pass_percent = round((passed_count / denominator) * 100, 2) if denominator else 0.0

    card1, card2, card3, card4 = st.columns(4)
    card1.metric("Total Tests", total_tests)
    card2.metric("Executions", total_executions)
    card3.metric("Pass %", f"{pass_percent}%")
    card4.metric("Failures", failed_count)


def _render_pie_chart(filtered_tests: pd.DataFrame, filtered_runs: pd.DataFrame) -> None:
    st.subheader("Pass vs Fail")

    if not filtered_tests.empty:
        pass_count = int((filtered_tests["Status"] == "Pass").sum())
        fail_count = int((filtered_tests["Status"] == "Fail").sum())
    elif not filtered_runs.empty:
        pass_count = int(pd.to_numeric(filtered_runs.get("passed", 0), errors="coerce").fillna(0).sum())
        fail_count = int(pd.to_numeric(filtered_runs.get("failed", 0), errors="coerce").fillna(0).sum())
    else:
        pass_count = 0
        fail_count = 0

    pie_df = pd.DataFrame(
        {
            "Status": ["Pass", "Fail"],
            "Count": [pass_count, fail_count],
        }
    )

    st.vega_lite_chart(
        pie_df,
        {
            "mark": {"type": "arc", "innerRadius": 40},
            "encoding": {
                "theta": {"field": "Count", "type": "quantitative"},
                "color": {"field": "Status", "type": "nominal"},
                "tooltip": [
                    {"field": "Status", "type": "nominal"},
                    {"field": "Count", "type": "quantitative"},
                ],
            },
            "width": 380,
            "height": 280,
        },
    )


def _render_feature_bar_chart(filtered_tests: pd.DataFrame) -> None:
    st.subheader("Feature-wise Status")
    if filtered_tests.empty:
        st.info("No test-level records available for selected filters.")
        return

    bar_df = (
        filtered_tests[filtered_tests["Status"].isin(["Pass", "Fail"])]
        .groupby(["Feature", "Status"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    if bar_df.empty:
        st.info("No pass/fail records available for feature chart.")
        return

    chart_ready = bar_df.set_index("Feature")
    st.bar_chart(chart_ready)


def _render_execution_trend(filtered_runs: pd.DataFrame, filtered_tests: pd.DataFrame) -> None:
    st.subheader("Execution Trend Over Time")
    if not filtered_runs.empty and "timestamp_obj" in filtered_runs.columns:
        trend_df = filtered_runs.copy()
        trend_df["DateTime"] = trend_df["timestamp_obj"]
        trend_plot = trend_df.set_index("DateTime")[["passed", "failed"]].fillna(0)
        st.line_chart(trend_plot)
        return

    if filtered_tests.empty:
        st.info("No run history or test-level timestamps available for trend chart.")
        return

    trend_df = (
        filtered_tests.dropna(subset=["TimestampObj"])
        .assign(Date=lambda frame: frame["TimestampObj"].dt.floor("h"))
        .groupby(["Date", "Status"])
        .size()
        .unstack(fill_value=0)
    )

    if trend_df.empty:
        st.info("No timestamped test data available for trend chart.")
        return

    st.line_chart(trend_df)


def _render_failed_table(filtered_tests: pd.DataFrame) -> None:
    st.subheader("Failed Tests")
    if filtered_tests.empty:
        st.info("No test-level records available.")
        return

    failed_df = filtered_tests[filtered_tests["Status"] == "Fail"].copy()
    if failed_df.empty:
        st.success("No failed tests in selected filter range.")
        return

    display_columns = [
        "RunID",
        "Environment",
        "User",
        "Feature",
        "TestType",
        "TestCase",
        "Status",
        "StartTime",
        "EndTime",
        "Timestamp",
        "ScreenshotPath",
    ]
    failed_df = failed_df[display_columns]

    column_config = {}
    if "ScreenshotPath" in failed_df.columns:
        try:
            column_config["ScreenshotPath"] = st.column_config.LinkColumn("Screenshot Path")
        except Exception:
            column_config = {}

    st.dataframe(failed_df, column_config=column_config)
    st.download_button(
        label="Download Failed Tests CSV",
        data=failed_df.to_csv(index=False).encode("utf-8"),
        file_name="failed_tests.csv",
        mime="text/csv",
    )


def _render_flaky_table(filtered_tests: pd.DataFrame) -> None:
    st.subheader("Flaky Tests")
    if filtered_tests.empty:
        st.info("No test-level records available.")
        return

    flaky_candidates = filtered_tests[filtered_tests["Status"].isin(["Pass", "Fail"])].copy()
    if flaky_candidates.empty:
        st.info("No pass/fail records available for flaky analysis.")
        return

    grouped = flaky_candidates.groupby("TestCase", dropna=False)
    rows: list[dict[str, Any]] = []
    for test_case, group in grouped:
        statuses = set(group["Status"].dropna().tolist())
        if not ({"Pass", "Fail"}.issubset(statuses)):
            continue

        sorted_group = group.sort_values(by="TimestampObj", na_position="last")
        latest = sorted_group.iloc[-1]
        rows.append(
            {
                "TestCase": test_case,
                "Executions": int(len(group)),
                "PassCount": int((group["Status"] == "Pass").sum()),
                "FailCount": int((group["Status"] == "Fail").sum()),
                "LatestStatus": latest.get("Status", "Unknown"),
                "LatestRunID": latest.get("RunID", ""),
                "LatestTimestamp": latest.get("Timestamp", ""),
                "Feature": latest.get("Feature", "Unknown"),
                "TestType": latest.get("TestType", "Unknown"),
            }
        )

    if not rows:
        st.success("No flaky tests detected under current filters.")
        return

    flaky_df = pd.DataFrame(rows).sort_values(by=["FailCount", "Executions"], ascending=False)
    st.dataframe(flaky_df)
    st.download_button(
        label="Download Flaky Tests CSV",
        data=flaky_df.to_csv(index=False).encode("utf-8"),
        file_name="flaky_tests.csv",
        mime="text/csv",
    )


def _render_unique_test_summary(filtered_tests: pd.DataFrame) -> None:
    st.subheader("Unique Test Cases Summary")
    if filtered_tests.empty:
        st.info("No test-level records available.")
        return

    sorted_df = filtered_tests.sort_values(by="TimestampObj", na_position="last")
    summary_rows: list[dict[str, Any]] = []
    for test_case, group in sorted_df.groupby("TestCase", dropna=False):
        latest = group.iloc[-1]
        summary_rows.append(
            {
                "TestCase": test_case,
                "Executions": int(len(group)),
                "LatestStatus": latest.get("Status", "Unknown"),
                "LatestRunID": latest.get("RunID", ""),
                "LatestTimestamp": latest.get("Timestamp", ""),
                "Feature": latest.get("Feature", "Unknown"),
                "TestType": latest.get("TestType", "Unknown"),
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values(by=["Feature", "TestCase"]) if summary_rows else pd.DataFrame()
    st.dataframe(summary_df)
    if not summary_df.empty:
        st.download_button(
            label="Download Unique Test Summary CSV",
            data=summary_df.to_csv(index=False).encode("utf-8"),
            file_name="unique_test_summary.csv",
            mime="text/csv",
        )


def _render_downloads() -> None:
    st.subheader("Report Downloads")
    if LATEST_HTML.exists():
        with LATEST_HTML.open("rb") as file:
            st.download_button(
                label="Download Latest HTML Report",
                data=file.read(),
                file_name="latest_report.html",
                mime="text/html",
            )
    else:
        st.info("Latest HTML report not found.")

    if HISTORY_FILE.exists():
        with HISTORY_FILE.open("rb") as file:
            st.download_button(
                label="Download Run History JSON",
                data=file.read(),
                file_name="run_history.json",
                mime="application/json",
            )


def _load_tc_run_history() -> pd.DataFrame:
    """Load per-TC execution history from tc_run_history.json."""
    payload = _safe_json_load(TC_HISTORY_FILE)
    if not isinstance(payload, list) or not payload:
        return pd.DataFrame(
            columns=["run_id", "run_timestamp", "env", "tc_number", "tc_name", "status"]
        )
    dataframe = pd.DataFrame(payload)
    if "run_timestamp" in dataframe.columns:
        dataframe["run_timestamp_obj"] = pd.to_datetime(
            dataframe["run_timestamp"], errors="coerce"
        )
    else:
        dataframe["run_timestamp_obj"] = pd.NaT
    return dataframe


def _render_tc_execution_history(tc_df: pd.DataFrame) -> None:
    st.subheader("TC Execution History (All Runs)")
    if tc_df.empty:
        st.info("No TC execution history found. Run tests to populate this view.")
        return

    # ── Sidebar filter for TC selection ────────────────────────────────
    available_tcs = sorted(tc_df["tc_name"].dropna().unique().tolist())
    selected_tcs = st.multiselect(
        "Filter by TC", options=available_tcs, default=available_tcs, key="tc_history_filter"
    )
    filtered = tc_df[tc_df["tc_name"].isin(selected_tcs)] if selected_tcs else tc_df

    # ── Summary pivot: TC x RunID ──────────────────────────────────────
    st.markdown("**Execution matrix — each cell shows PASS/FAIL per TC per run:**")
    pivot_data: dict[str, dict[str, str]] = {}
    for _, row in filtered.iterrows():
        tc = str(row.get("tc_name", ""))
        run = str(row.get("run_id", ""))
        status = str(row.get("status", ""))
        pivot_data.setdefault(tc, {})[run] = status

    if pivot_data:
        pivot_df = pd.DataFrame(pivot_data).T.reset_index()
        pivot_df = pivot_df.rename(columns={"index": "TC"})
        # Sort columns so runs are in chronological order
        run_cols = [c for c in pivot_df.columns if c != "TC"]
        run_cols_sorted = sorted(run_cols)
        pivot_df = pivot_df[["TC"] + run_cols_sorted]
        st.dataframe(pivot_df, use_container_width=True)

    # ── Full detail table ───────────────────────────────────────────────
    st.markdown("**All TC executions (detailed):**")
    detail_cols = ["run_id", "run_timestamp", "env", "tc_name", "status"]
    detail_df = filtered[[c for c in detail_cols if c in filtered.columns]].copy()
    detail_df = detail_df.sort_values(by=["tc_name", "run_timestamp"], ascending=[True, False])
    st.dataframe(detail_df, use_container_width=True)

    # ── Per-TC pass rate summary ──────────────────────────────────────
    st.markdown("**Per-TC pass rate summary:**")
    summary_rows = []
    for tc_name, group in filtered.groupby("tc_name", dropna=False):
        executions = len(group)
        passes = int((group["status"] == "PASS").sum())
        failures = int((group["status"] == "FAIL").sum())
        pass_rate = round((passes / executions) * 100, 1) if executions else 0.0
        latest_row = group.sort_values("run_timestamp", ascending=False).iloc[0]
        summary_rows.append(
            {
                "TC Name": tc_name,
                "Total Executions": executions,
                "Passed": passes,
                "Failed": failures,
                "Pass Rate %": pass_rate,
                "Latest Run ID": latest_row.get("run_id", ""),
                "Latest Status": latest_row.get("status", ""),
                "Latest Timestamp": latest_row.get("run_timestamp", ""),
                "Env": latest_row.get("env", ""),
            }
        )
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows).sort_values("TC Name")
        st.dataframe(summary_df, use_container_width=True)
        st.download_button(
            label="Download TC History CSV",
            data=detail_df.to_csv(index=False).encode("utf-8"),
            file_name="tc_run_history.csv",
            mime="text/csv",
        )


def main() -> None:
    _ensure_required_folders()

    st.set_page_config(page_title="DocuChat Automation Dashboard", layout="wide")
    st.title("DocuChat Automation Dashboard")
    st.caption("Filter-driven test analytics using existing report history and archived Allure results")

    tests_df = _load_all_test_records()
    runs_df = _load_run_history()
    tc_history_df = _load_tc_run_history()

    filtered_tests, filtered_runs = _apply_filters(tests_df=tests_df, runs_df=runs_df)

    if filtered_tests.empty and filtered_runs.empty and tc_history_df.empty:
        st.warning("No report data found for selected filters.")
        _render_downloads()
        return

    _render_summary_cards(filtered_tests=filtered_tests, filtered_runs=filtered_runs, all_tests_df=tests_df)

    row_a_left, row_a_right = st.columns(2)
    with row_a_left:
        _render_pie_chart(filtered_tests=filtered_tests, filtered_runs=filtered_runs)
    with row_a_right:
        _render_feature_bar_chart(filtered_tests=filtered_tests)

    _render_execution_trend(filtered_runs=filtered_runs, filtered_tests=filtered_tests)
    _render_tc_execution_history(tc_history_df)
    _render_failed_table(filtered_tests=filtered_tests)
    _render_flaky_table(filtered_tests=filtered_tests)
    _render_unique_test_summary(filtered_tests=filtered_tests)
    _render_downloads()


if __name__ == "__main__":
    if _is_running_in_streamlit():
        main()
    else:
        raise SystemExit(_launch_via_streamlit())
