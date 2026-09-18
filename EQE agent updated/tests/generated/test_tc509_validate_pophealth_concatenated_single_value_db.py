"""TC-509 (qTest ID 278659) - Validate concatenated PopHealthStreamConcatenated
field with single HS value set

Type        : Database
Description : Verify that when a member has exactly one Pop Stream flag set to 1,
              the view returns the correct HS code in PopHealthStreamConcatenated
              with no delimiters.
Pre-condition: Access to EDWStageDB CareModel server 72 with read permissions on
               view VwAnalytics_SDOH_PopStreamByMemberMonth_Codified.
               Test data loaded with one Pop Stream flag set to 1 for a member-month.
Environment : Configured via --env and --product-area flags (reads from Agent/environments.yaml)
ADO Work Item: 731949
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

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


# ── Known HS code mappings (from acceptance criteria) ────────────────────────
# Each Pop Stream column maps to a predefined HS code.
# This list should match the view's concatenation order.
_HS_CODE_COLUMNS = {
    "HealthyChildren":    "HS01",
    "HealthyAdults":      "HS02",
    "AdultswithCC":       "HS11",
    "OlderAdults":        "HS12",
    # TODO: confirm full list of Pop Stream columns and HS code mappings
    #       from VwAnalytics_SDOH_PopStreamByMemberMonth_Codified DDL
}


async def _run_tc_flow(db_connection, tc_name: str = "TC-509") -> None:
    """Shared test flow — one _run_step per qTest test step."""
    cursor = db_connection.cursor()

    # ── Step 1: Connect to EDWStageDB CareModel server 72 ───────────────────
    async def _step_1():
        # Connection is already established via the db_connection fixture.
        # Verify connectivity by running a trivial query.
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result is not None, "Database connection check failed"
        assert result[0] == 1, f"Expected 1, got {result[0]}"

    await _run_step(1, "Connect to EDWStageDB CareModel server 72 using SQL client", _step_1(), tc_name)

    # ── Step 2: Query the view for a member-month with exactly one flag ──────
    async def _step_2():
        # Find a member-month where exactly one Pop Stream flag is set to 1
        # and PopHealthStreamConcatenated is populated.
        cursor.execute("""
            SELECT TOP 1
                MemberID,
                MemberMonthID,
                PopHealthStreamConcatenated,
                HealthyChildren,
                HealthyAdults,
                AdultswithCC,
                OlderAdults
            FROM [EDWStageDB].[CareModel].[VwAnalytics_SDOH_PopStreamByMemberMonth_Codified]
            WHERE PopHealthStreamConcatenated IS NOT NULL
              AND LEN(PopHealthStreamConcatenated) > 0
              AND PopHealthStreamConcatenated NOT LIKE '%|%'
        """)
        row = cursor.fetchone()
        assert row is not None, (
            "No member-month found with exactly one Pop Stream flag set. "
            "Ensure test data exists in the view."
        )
        # Store for subsequent steps
        _run_tc_flow._single_flag_row = row

    await _run_step(2, "Execute SELECT query filtering for a member-month with one Pop Stream flag set to 1", _step_2(), tc_name)

    # ── Step 3: Retrieve and validate PopHealthStreamConcatenated value ───────
    async def _step_3():
        row = _run_tc_flow._single_flag_row
        concat_value = row.PopHealthStreamConcatenated
        assert concat_value is not None, "PopHealthStreamConcatenated is NULL for single-flag row"
        assert "|" not in concat_value, (
            f"Expected no pipe delimiter for single flag, but got: '{concat_value}'"
        )
        # Store for next steps
        _run_tc_flow._concat_value = concat_value

    await _run_step(3, "Retrieve PopHealthStreamConcatenated field value from the query result", _step_3(), tc_name)

    # ── Step 4: Verify HS code matches predefined mapping ────────────────────
    async def _step_4():
        concat_value = _run_tc_flow._concat_value
        valid_hs_codes = set(_HS_CODE_COLUMNS.values())
        assert concat_value in valid_hs_codes, (
            f"PopHealthStreamConcatenated value '{concat_value}' is not a valid HS code. "
            f"Expected one of: {sorted(valid_hs_codes)}"
        )

    await _run_step(4, "Verify HS code matches predefined mapping (HS01, HS02, HS11, HS12)", _step_4(), tc_name)

    # ── Step 5: Verify no trailing or leading pipe delimiters ────────────────
    async def _step_5():
        concat_value = _run_tc_flow._concat_value
        assert not concat_value.startswith("|"), (
            f"Leading pipe delimiter found: '{concat_value}'"
        )
        assert not concat_value.endswith("|"), (
            f"Trailing pipe delimiter found: '{concat_value}'"
        )

    await _run_step(5, "Verify no trailing or leading pipe delimiters exist in the field", _step_5(), tc_name)

    # ── Step 6: Confirm other Pop Stream flags are 0 or NULL ─────────────────
    async def _step_6():
        row = _run_tc_flow._single_flag_row
        concat_value = _run_tc_flow._concat_value

        # Determine which column should be set based on the HS code
        expected_column = None
        for col_name, hs_code in _HS_CODE_COLUMNS.items():
            if hs_code == concat_value:
                expected_column = col_name
                break

        # Check that exactly one flag is set to 1
        flag_columns = ["HealthyChildren", "HealthyAdults", "AdultswithCC", "OlderAdults"]
        set_flags = []
        for col in flag_columns:
            val = getattr(row, col, None)
            if val == 1:
                set_flags.append(col)

        assert len(set_flags) == 1, (
            f"Expected exactly 1 flag set to 1, but found {len(set_flags)}: {set_flags}"
        )
        if expected_column:
            assert set_flags[0] == expected_column, (
                f"Flag '{set_flags[0]}' is set but HS code '{concat_value}' "
                f"maps to column '{expected_column}'"
            )

    await _run_step(6, "Confirm that other Pop Stream flags for this member-month are 0 or NULL", _step_6(), tc_name)

    # ── Step 7: Document result and compare with expected output ──────────────
    async def _step_7():
        row = _run_tc_flow._single_flag_row
        concat_value = _run_tc_flow._concat_value

        # Final cross-validation: re-query with explicit member to confirm
        cursor.execute("""
            SELECT PopHealthStreamConcatenated
            FROM [EDWStageDB].[CareModel].[VwAnalytics_SDOH_PopStreamByMemberMonth_Codified]
            WHERE MemberID = ?
              AND MemberMonthID = ?
        """, (row.MemberID, row.MemberMonthID))
        verify_row = cursor.fetchone()
        assert verify_row is not None, "Re-query for same member returned no results"
        assert verify_row.PopHealthStreamConcatenated == concat_value, (
            f"Re-query value '{verify_row.PopHealthStreamConcatenated}' "
            f"does not match original '{concat_value}'"
        )

    await _run_step(7, "Document the result and compare with expected output", _step_7(), tc_name)

    # Cleanup
    cursor.close()


@pytest.mark.db
@pytest.mark.regression
async def test_validate_pophealth_concatenated_single_value(db_connection):
    """TC-509: Validate PopHealthStreamConcatenated field with single HS value set."""
    await _run_tc_flow(db_connection, tc_name="TC-509")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "--env=qa", "--product-area=clinical_automation", "-vv", "-s"]))
