"""Live end-to-end test: submit a real defect to qTest and print the result."""
import sys
sys.path.insert(0, "Qtest_connection")
from Defect import submit_playwright_failure, extract_defect_url, QTEST_HOST, QTEST_PROJECT_ID

print(f"Submitting test defect to qTest: host={QTEST_HOST} project={QTEST_PROJECT_ID}")

result = submit_playwright_failure(
    {
        "title": "[AUTO-TEST] DocuChat - Playwright Integration Verification",
        "error_message": "This is a verification defect — safe to close/reject.",
        "file": "tests/web/chat/test_tc013.py",
        "browser": "chromium",
        "status": "failed",
        "duration_ms": 5000,
        "retry": 0,
        "stack_trace": "AssertionError: Verification defect created by _qtest_live_test.py",
    }
)

defect_id  = result.get("id", "")
defect_pid = result.get("pid", "")
defect_url = extract_defect_url(result)

print(f"\n[SUCCESS] Defect created!")
print(f"  ID  : {defect_id}")
print(f"  PID : {defect_pid}")
print(f"  URL : {defect_url}")
print(f"  Direct qTest URL: {defect_url}")
print(f"\nFull response keys: {list(result.keys())}")
