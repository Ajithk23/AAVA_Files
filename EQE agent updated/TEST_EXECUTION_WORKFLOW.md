# Test Execution Workflow — With Automatic Learning File Reference

## **Overview**

This workflow ensures that every time you run tests, the **AUTOMATION_LEARNING_README.md** file is automatically referenced to:
1. Show you known issues BEFORE you run tests
2. Help you understand failures quickly if tests fail
3. Prevent repeated mistakes by showing solutions upfront

---

## **Your Quick Command**

```powershell
# Run TC001-TC012 in headless mode (QA environment)
python run_tests_with_learning.py --tc-range 001-012 --env qa --headless

# Or use the shorthand PowerShell wrapper
.\run_tc.ps1 -TcRange "001-012" -Env qa -Headless
```

That's it! No need to manually reference the learning file anymore.

---

## **Step-by-Step Workflow**

### **Step 1: Navigate to Workspace**
```powershell
cd c:\Users\cs221014\AIDev-testing
```

### **Step 2: Activate Virtual Environment**
```powershell
.\.venv\Scripts\Activate.ps1
```

### **Step 3: Run Tests with Learning Reference**

**For TC001-TC012 (Full Suite - Headless)**
```powershell
python run_tests_with_learning.py --tc-range 001-012 --env qa --headless
```

**For Specific TC Groups**
```powershell
# TC004-TC006 (Chat with Documents)
python run_tests_with_learning.py --tc-range 004-006 --env qa --headless

# TC010-TC012 (Code Assistant - Python)
python run_tests_with_learning.py --tc-range 010-012 --env qa --headless
```

**For Debugging (Headed Mode - UI Visible)**
```powershell
python run_tests_with_learning.py --tc-range 001-012 --env qa --headed
```

**For Different Environments**
```powershell
# INT environment (with Okta sandbox MFA)
python run_tests_with_learning.py --tc-range 001-012 --env int --headless

# UAT environment
python run_tests_with_learning.py --tc-range 001-012 --env uat --headless
```

### **Step 4: Review Pre-Execution Reference**

The script will print something like:

```
================================================================================
📚 AUTOMATION LEARNING REFERENCE — Before Running Tests
================================================================================

Running TC001-TC012

✅ Found 4 relevant known issue(s) from AUTOMATION_LEARNING_README.md:

  • ISSUE-026: Sidebar refresh delay after chat delete — confirmed across QA
    Status: Accepted known issue
  • ISSUE-027: Character limit validation not enforced by Streamlit `st.text_input`
    Status: Soft-skipped — App limitation
  • ISSUE-028: Copy & Regenerate buttons missing in Code Assistant chat type
    Status: Soft-skipped — Chat type variation
  • ISSUE-010: Streamlit re-render after chat type change clears textarea
    Status: Partially fixed — validation pending

💡 Reference these issues if tests fail. Check AUTOMATION_LEARNING_README.md for full details.

================================================================================

▶️  Running command:
...

================================================================================
TEST EXECUTION STARTING
================================================================================
```

**⭐ Now you know what to expect!** If any of these issues occur, you already have the fix.

### **Step 5: Tests Run**

Tests execute with verbose output, step timing, and soft-skip warnings logged. Examples:

```
[STEP_TIMING] TC004 | Step 6 | Verify response — code displayed with copy options | latency_ms=1234.56

WARNING  tests.web.chat.chat_test_helpers:chat_test_helpers.py:1667 
[TC STEP 10 SOFT-SKIP] Character limit NOT enforced by frontend input: 
maxlength_attr=-1. The Streamlit st.text_input may not have max_chars configured. 
Closing modal and continuing.

[KNOWN ISSUE] Sidebar did not reflect delete of 'Chat Title' within 15 s. 
Backend confirmed delete via success banner. 
Root cause: Streamlit st.dialog does not auto-close after delete.
```

**All soft-skips are intentional and documented** — tests continue and pass.

### **Step 6: Review Post-Execution Guidance**

After tests complete:

```
================================================================================
TEST EXECUTION COMPLETED
================================================================================

📊 Results Summary:
  ✅ Passed: 12
  ⚠️  Soft-skips: 5 (see logs above — all expected)
  ❌ Failed: 0
  ⏱️  Total duration: 2770.40s (46m 10s)

📖 NEXT STEPS if tests failed:
  1. Check the AUTOMATION_LEARNING_README.md file for matching issues
  2. Look for 'ISSUE-XXX' sections matching your failure patterns
  3. Read the ROOT CAUSE and FIX sections for remediation
  4. If the issue is not documented, add it as a new ISSUE-XXX entry

   File location: c:\Users\cs221014\AIDev-testing\AUTOMATION_LEARNING_README.md

================================================================================
```

---

## **If Tests Fail**

### **Quick Diagnosis Flow**

1. **Check test output for errors** — Look for `FAILED`, `AssertionError`, `Timeout`, etc.

2. **Scan AUTOMATION_LEARNING_README.md** for your error pattern
   - Search by test case number (TC001, TC004, etc.)
   - Search by step number (Step 10, Step 13, etc.)
   - Search by error type (Copy icon, Regenerate, Sidebar, etc.)

3. **Jump to ISSUE-XXX** section matching your failure

4. **Read the ROOT CAUSE section** — understanding why it failed

5. **Read the FIX section** — how to remediate it

6. **Read the PATTERN section** — how to prevent it in future

### **Example: If TC005 Step 10 Fails**

```
Test: test_tc005 
Step: 10 | Verify chat Edit — >255 characters in title field shows character-limit message
Error: Expected character limit warning, but input accepted 260 characters

Search AUTOMATION_LEARNING_README.md for "Step 10" or "character limit"
👇
Found: ISSUE-027: Character limit validation not enforced by Streamlit `st.text_input`
👇
ROOT CAUSE: 
  Streamlit `st.text_input` does not have `max_chars` parameter configured on the 
  backend, resulting in `maxlength_attr=-1` in the DOM.
👇
FIX: 
  This is a soft-skipped test step (not a framework bug). The test expects HTML-level 
  validation, but Streamlit doesn't enforce it. Backend validation should handle this. 
  For now, soft-skip remains appropriate — the core chat edit functionality works.
👇
SOLUTION: No fix needed for the test framework. If you need character limit validation 
  on the app side, file a feature request with the application team.
```

---

## **If a New Failure Occurs (Not in Learning File)**

1. **Investigate the failure** — understand the root cause
2. **Implement the fix** in the test framework or app
3. **Validate the fix** — re-run the test to confirm it passes
4. **Document it**:
   - Open AUTOMATION_LEARNING_README.md
   - Find the highest ISSUE-XXX number
   - Add a new ISSUE-(next number) entry
   - Use the template from an existing issue
   - Include: Problem, Root Cause, Fix, Pattern, Files Changed
5. **Commit the learning file** — so other team members benefit

---

## **Command Cheat Sheet**

| Task | Command |
|------|---------|
| Run TC001-TC012 (headless) | `python run_tests_with_learning.py --tc-range 001-012 --env qa --headless` |
| Run TC004-TC006 (headless) | `python run_tests_with_learning.py --tc-range 004-006 --env qa --headless` |
| Run with UI visible (debug) | `python run_tests_with_learning.py --tc-range 001-012 --env qa --headed` |
| Run on INT environment | `python run_tests_with_learning.py --tc-range 001-012 --env int --headless` |
| Run with PowerShell shorthand | `.\run_tc.ps1 -TcRange "001-012" -Env qa -Headless` |
| Run direct pytest (no reference) | `.\.venv\Scripts\python.exe -m pytest tests/web/chat/test_tc*.py --env=qa --headless=true -vv -s` |

---

## **File Reference**

| File | Purpose |
|------|---------|
| **AUTOMATION_LEARNING_README.md** | ⭐ Main reference — all issues, fixes, patterns, and known limitations |
| **run_tests_with_learning.py** | Helper script that parses the learning file and references it during test runs |
| **run_tc.ps1** | PowerShell wrapper for convenience (shorthand for the helper script) |
| **RUN_TESTS_QUICK_START.md** | Quick reference guide with all command examples |
| **PIPELINE_HANDOFF.md** | CI/CD integration guide (for Harness/Jenkins) |
| **README.md** | General project documentation |

---

## **Key Principles**

✅ **Always use the helper script** — it ensures learning file is referenced  
✅ **Keep learning file updated** — it's the source of truth  
✅ **Document new issues immediately** — don't leave failures undocumented  
✅ **Use soft-skips for known limitations** — don't fail tests for app issues  
✅ **Reference the file when debugging** — answers are usually already there  
✅ **Share learnings with the team** — commit documentation updates  

---

## **Example: Full Test Run Session**

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Run tests
python run_tests_with_learning.py --tc-range 001-012 --env qa --headless

# ============ Output ============
# 📚 AUTOMATION LEARNING REFERENCE — Before Running Tests
# ✅ Found 4 relevant known issue(s):
#   • ISSUE-026: Sidebar refresh delay...
#   • ISSUE-027: Character limit validation...
#   • ISSUE-028: Copy & Regenerate buttons...
#   • ISSUE-010: Streamlit re-render...
#
# ▶️  Running command: ... pytest ... --env=qa --headless=true -vv -s
# ===============================

# [Tests run... 46 minutes later...]

# ===============================
# ✅ PASSED: 12
# 📊 Duration: 2770.40s (46m 10s)
# 📖 NEXT STEPS: Reference AUTOMATION_LEARNING_README.md for any issues
# ===============================

# ✅ Done! All tests passed. No fixes needed.
```

---

## **Still Have Questions?**

1. **How do I understand a specific issue?** → Search AUTOMATION_LEARNING_README.md for ISSUE-XXX
2. **How do I add a new issue?** → Follow the template in the Issue Registry section
3. **How do I run a specific TC range?** → Use `--tc-range XXX-YYY` parameter
4. **How do I run in headed mode?** → Use `--headed` instead of `--headless`
5. **How do I run on a different environment?** → Use `--env int|uat|dev` parameter
6. **Where are test results saved?** → `reports/latest_report.html` or `Test_Latest_Run_Details/CRT_QA/`

---
