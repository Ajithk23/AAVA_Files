# Quick Start — Running Test Cases with Learning File Reference

## **Command to Run TC001-TC012 (Headless Mode)**

### **Option 1: Using Helper Script (Recommended — Includes Learning File Reference)**

```powershell
# Navigate to workspace
cd c:\Users\cs221014\AIDev-testing

# Activate venv (if not already active)
.\.venv\Scripts\Activate.ps1

# Run TC001-TC012 with automatic AUTOMATION_LEARNING_README.md reference
python run_tests_with_learning.py --tc-range 001-012 --env qa --headless

# Run specific TC range
python run_tests_with_learning.py --tc-range 004-006 --env qa --headless

# Run with headed mode (UI visible for debugging)
python run_tests_with_learning.py --tc-range 001-012 --env qa --headed

# Run on different environment
python run_tests_with_learning.py --tc-range 001-012 --env int --headless
```

**What this does:**
✅ Parses AUTOMATION_LEARNING_README.md for your TC range  
✅ Prints known issues BEFORE test execution (so you know what to expect)  
✅ Runs the tests with pytest  
✅ Provides guidance AFTER execution if tests fail  

---

### **Option 2: Direct Pytest Command (No Helper Script)**

```powershell
# Navigate to workspace
cd c:\Users\cs221014\AIDev-testing

# Activate venv
.\.venv\Scripts\Activate.ps1

# Run TC001-TC012 directly
.\.venv\Scripts\python.exe -m pytest `
  tests/web/chat/test_tc001_tc002_tc003_regression_docuchat_chat_validate_chat_initialization_basic_chat.py `
  tests/web/chat/test_tc004_tc005_tc006_chat_initialization_chat_with_documents.py `
  tests/web/chat/test_tc007_tc008_tc009_chat_initialization_document_review.py `
  tests/web/chat/test_tc010_tc011_tc012_regression_docuchat_chat_validate_chat_initialization_code_assistant_python.py `
  --env=qa --headless=true -vv -s
```

---

## **Quick Reference: Run Specific TC Groups**

| TC Range | Command |
|----------|---------|
| **TC001-TC003** (Basic Chat) | `python run_tests_with_learning.py --tc-range 001-003 --env qa --headless` |
| **TC004-TC006** (Chat with Documents) | `python run_tests_with_learning.py --tc-range 004-006 --env qa --headless` |
| **TC007-TC009** (Document Review) | `python run_tests_with_learning.py --tc-range 007-009 --env qa --headless` |
| **TC010-TC012** (Code Assistant - Python) | `python run_tests_with_learning.py --tc-range 010-012 --env qa --headless` |
| **TC001-TC012** (Full Suite) | `python run_tests_with_learning.py --tc-range 001-012 --env qa --headless` |

---

## **What Happens When You Run:**

### **1. Before Tests Start**
```
================================================================================
📚 AUTOMATION LEARNING REFERENCE — Before Running Tests
================================================================================

Running TC001-TC012

✅ Found 3 relevant known issue(s) from AUTOMATION_LEARNING_README.md:

  • ISSUE-026: Sidebar refresh delay after chat delete — confirmed across QA
    Status: Accepted known issue
  • ISSUE-027: Character limit validation not enforced by Streamlit `st.text_input`
    Status: Soft-skipped — App limitation
  • ISSUE-028: Copy & Regenerate buttons missing in Code Assistant chat type
    Status: Soft-skipped — Chat type variation

💡 Reference these issues if tests fail. Check AUTOMATION_LEARNING_README.md for full details.

================================================================================
```

### **2. During Tests**
- Tests execute with `-vv -s` flags for verbose output
- Steps are logged with timing information
- Soft-skips are logged with warnings (but don't fail the test)
- Known issues are noted in the logs

### **3. After Tests Complete**
```
================================================================================
TEST EXECUTION COMPLETED
================================================================================

📖 NEXT STEPS if tests failed:
  1. Check the AUTOMATION_LEARNING_README.md file for matching issues
  2. Look for 'ISSUE-XXX' sections matching your failure patterns
  3. Read the ROOT CAUSE and FIX sections for remediation
  4. If the issue is not documented, add it as a new ISSUE-XXX entry

   File location: c:\Users\cs221014\AIDev-testing\AUTOMATION_LEARNING_README.md
================================================================================
```

---

## **Environment Options**

```powershell
# QA (default) — recommended for regression tests
--env qa

# INT (Integration/Sandbox) — for testing with Okta MFA
--env int

# DEV — development environment
--env dev

# UAT — user acceptance testing
--env uat
```

---

## **Headless vs Headed Mode**

```powershell
# Headless (default) — no browser UI, faster, for CI/CD
--headless

# Headed (UI visible) — helpful for debugging
--headed
```

---

## **Checking Test Results**

After tests complete, check these locations:

```powershell
# HTML report (open in browser)
reports\latest_report.html

# Run summary markdown
Test_Latest_Run_Details\CRT_QA\QA_Chat_TC001_TC012_Run_Summary_*.md

# Archived reports
reports\archive\*

# Screenshots of failures
reports\screenshots\2026-04-22\fail\*
```

---

## **Troubleshooting Quick Links**

If you encounter issues, jump directly to the relevant section in AUTOMATION_LEARNING_README.md:

| Issue | Section | Quick Link |
|-------|---------|-----------|
| Test fails with unknown mark warning | ISSUE-001 | Search: `temporary_chat pytest mark` |
| Parametrized test blocked by policy | ISSUE-002 | Search: `item.originalname` |
| Tips & Tricks counted as response | ISSUE-003 | Search: `false-positive AI response` |
| Model name mismatch | ISSUE-004, ISSUE-019 | Search: `4.1 mini CRT vs 4.1-mini CRT` |
| Copy icon / Regenerate not found | ISSUE-005, ISSUE-028 | Search: `hover target` |
| Response timeout | ISSUE-007 | Search: `60 seconds` |
| Character limit not enforced | ISSUE-027 | Search: `maxlength_attr` |
| Sidebar delete delay | ISSUE-026 | Search: `Streamlit WebSocket` |

---

## **Pro Tips**

1. **Always run the helper script first** — it shows you what known issues apply to your TC range
2. **Check the markdown before debugging** — the answer is usually in AUTOMATION_LEARNING_README.md
3. **Add new issues immediately** — if a failure isn't in the learning file, add ISSUE-XXX after you fix it
4. **Use soft-skips wisely** — they indicate known limitations, not bugs
5. **Keep learning file updated** — it's the source of truth for the framework

---

## **When to Update AUTOMATION_LEARNING_README.md**

Add a new ISSUE-XXX entry when:
- ✅ You discover a failure that isn't in the file
- ✅ You find a new pattern or anti-pattern
- ✅ You implement a fix that others should know about
- ✅ You identify a chat-type or environment-specific behavior

**Format**: Use the template in the "Issue Registry" section of the learning file.

---
