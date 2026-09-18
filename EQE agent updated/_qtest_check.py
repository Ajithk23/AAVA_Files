"""Quick sanity check on qTest integration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "Qtest_connection"))
sys.path.insert(0, str(Path(__file__).parent))

# 1. Import Defect.py
try:
    from Defect import (
        submit_playwright_failure,
        build_playwright_defect_properties,
        QTEST_HOST,
        QTEST_TOKEN,
        QTEST_PROJECT_ID,
        PLAYWRIGHT_FAIL_SEVERITY,
    )
    print(f"[OK] Defect.py import succeeded")
    print(f"     Host={QTEST_HOST} | Project={QTEST_PROJECT_ID}")
except Exception as e:
    print(f"[FAIL] Defect.py import: {e}")

# 2. Import as conftest does (package path)
try:
    from Qtest_connection.Defect import submit_playwright_failure as _spf, PlaywrightTestResult as _PR
    print(f"[OK] conftest-style import (Qtest_connection.Defect) succeeded")
except Exception as e:
    print(f"[FAIL] conftest-style import: {e}")

# 3. review_defects.py import
try:
    from review_defects import _load_pending, _save_pending, _PENDING_FILE, _submit_to_qtest
    print(f"[OK] review_defects.py import succeeded")
    entries = _load_pending()
    pending = [e for e in entries if e.get("status") == "pending"]
    approved = [e for e in entries if e.get("status") == "approved"]
    rejected = [e for e in entries if e.get("status") == "rejected"]
    print(f"     pending_defects.json: {len(entries)} total | {len(pending)} pending | {len(approved)} approved | {len(rejected)} rejected")
    for e in entries:
        print(f"     [{e.get('status','?'):8s}] {e.get('test_nodeid','')[:70]}")
except Exception as e:
    print(f"[FAIL] review_defects.py import: {e}")

# 4. Build a sample payload (no network call)
try:
    props = build_playwright_defect_properties({
        "title": "SAMPLE - TC013 Step 4 failed",
        "error_message": "Model option not visible",
        "browser": "chromium",
        "status": "failed",
        "duration_ms": 38000,
    })
    print(f"[OK] build_playwright_defect_properties returned {len(props)} properties")
    for p in props:
        val = str(p.get("field_value", ""))[:60]
        print(f"     field_id={p['field_id']:4d}  {p.get('field_name',''):<15s}  {val}")
except Exception as e:
    print(f"[FAIL] build payload: {e}")
