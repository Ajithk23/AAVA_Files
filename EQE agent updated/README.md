# DocuChat Automation Framework

Enterprise-ready Python Playwright + Pytest automation platform for the **DocuChat** application.

## Application
- Name: DocuChat
- URL (QA): `https://docu-chat.crt.ai.caresource.corp/`
- Features under test:
  - Chat
  - File Handling
  - Prompt Library

## Framework Capabilities
- Feature-based test routing
- Page Object Model (POM)
- Centralized locator repository with fallback/self-healing
- Parallel execution (`-n auto`)
- Retry handling for flaky tests
- Environment switching (`dev`, `qa`, `uat`)
- Automatic per-run runtime validation (environment reachability + app version capture)
- Automatic per-test execution checks (latency, UI visibility, network validation, screenshots on pass/fail)
- Tag-based execution
- Reporting (`pytest-html`, `allure`, screenshots, logs)
- Execution history tracking (`reports/history/run_history.json`)
- Streamlit dashboard (trend + downloadable reports)
- Scheduling:
  - Local scheduler script (`run_scheduler.py`)
  - GitHub Actions daily/manual/push workflow
- Multi-user collaboration via Git + branch/PR workflow

## Project Structure

```text
DocuChat/
├── tests/
│   ├── web/
│   │   ├── conftest.py                         # Page-object fixtures: chat_page / file_page / prompt_page
│   │   ├── chat/
│   │   │   ├── test_chat_send_message.py        # smoke
│   │   │   ├── test_chat_empty_message.py       # regression
│   │   │   ├── test_chat_long_message.py        # regression
│   │   │   └── test_chat_response_within_timeout.py  # regression + flaky
│   │   ├── file_handling/
│   │   │   ├── test_file_upload_success.py      # regression
│   │   │   ├── test_file_upload_invalid_type.py # regression
│   │   │   └── test_file_upload_large_file.py   # smoke
│   │   └── prompt_library/
│   │       ├── test_prompt_search_and_apply.py  # sanity
│   │       ├── test_prompt_search_no_results.py # regression
│   │       └── test_prompt_search_empty_term.py # sanity
├── pages/
│   ├── base_page.py
│   ├── chat_page.py
│   ├── file_handling_page.py
│   └── prompt_library_page.py
├── locators/
│   ├── chat_locators.py
│   ├── file_handling_locators.py
│   ├── prompt_library_locators.py
│   └── self_healing_cache.json
├── utils/
│   ├── config_loader.py
│   ├── feature_router.py
│   ├── history_tracker.py
│   ├── locator_engine.py
│   ├── locator_guard.py
│   ├── logger.py
│   └── policy_guard.py
├── config/
│   └── config.yaml
├── reports/
│   ├── history/run_history.json
│   ├── screenshots/
│   └── allure-results/
├── logs/
├── dashboard/
│   └── app.py
├── test_data/
│   ├── sample_upload.txt
│   ├── sample_policy.txt
│   ├── sample_prompts.csv
│   └── test_inputs.json
├── .github/workflows/
│   └── run_tests.yml
├── conftest.py
├── pytest.ini
├── requirements.txt
├── run_tests.py
├── run_scheduler.py
├── run_history_report.py
└── README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run Tests

### Run all tests
```bash
pytest --env=qa
```

### Run single test
```bash
pytest tests/web/chat/test_chat_send_message.py --env=qa
```

### Run feature folder
```bash
pytest tests/web/file_handling --env=qa
```

### Run by tags
```bash
pytest -m "smoke and chat" --env=qa
pytest -m regression --env=uat
```

### Optional helper launcher
```bash
python run_tests.py --env qa
python run_tests.py --feature chat --env qa
python run_tests.py --tag "smoke and chat" --env qa
python run_tests.py --test tests/web/chat/test_chat_send_message.py --env qa
```

## Environments
Configured in `config/config.yaml`.

Supported: `dev`, `qa`, `uat`.

CLI switch:
```bash
pytest --env=dev
pytest --env=qa
pytest --env=uat
```

## Reporting
- HTML report: `reports/latest_report.html`
- Allure raw results: `reports/allure-results`
- Pass and failure screenshots: `reports/screenshots`
- Logs per run: `logs/`
- Runtime validation snapshots: `reports/history/validations`

Validation behavior flags:
```bash
# Default: checks always run and are logged
pytest --env=qa

# Optional strict enforcement (fail test on validation issues)
pytest --env=qa --strict-network-validation --strict-ui-validation
```

Generate Allure report locally:
```bash
allure serve reports/allure-results
```

## Execution History Tracking
Each test session appends:
- run count
- passed
- failed
- duration
- timestamp

Saved to:
- `reports/history/run_history.json`

## AI Dashboard
Run:
```bash
streamlit run dashboard/app.py
```

Dashboard includes:
- total runs
- latest pass %
- failure trend
- flaky/failed run view
- date filtering
- downloadable HTML report
- downloadable execution history JSON
- downloadable filtered CSV export
- full execution table

## Scheduling

### Option 1 (Default): Local Scheduler
`run_scheduler.py` supports one-time, daily, and cron mode.

```bash
python run_scheduler.py --mode once --env qa
python run_scheduler.py --mode daily --time 02:00 --env qa
python run_scheduler.py --mode cron --cron "0 2 * * *" --env qa
```

Windows Task Scheduler example action:
```bash
python C:\path\to\DocuChat\run_scheduler.py --mode once --env qa
```

### Option 2 (Optional): GitHub Actions
Workflow file:
- `.github/workflows/run_tests.yml`

Triggers:
- daily schedule
- manual trigger
- push trigger

Artifacts:
- pytest HTML report
- allure results
- failure screenshots

## Locator Strategy (Mandatory Priority)
Priority order:
1. `data-testid`
2. `get_by_role`
3. `text`
4. `css`
5. `relative`
6. `xpath` fallback

Additional rules:
- Keep locators only in `locators/`
- Reuse existing locators before adding new
- Implement fallback candidate list
- Auto-attempt next locator if previous fails
- Log fallback usage
- Avoid duplicates
- Use self-healing cache (`locators/self_healing_cache.json`)

## AI Automation Framework Rules
When generating new tests:
1. Read current folder structure.
2. Read existing files in `locators/`, `pages/`, `utils/`.
3. Reuse existing code and methods.
4. Follow naming convention strictly.
5. Do **not** regenerate framework.
6. Extend only what is needed.
7. Ensure generated web tests use the framework fixtures (`docuchat_context`/`chat_page`/`file_page`/`prompt_page`) so automatic execution validations are applied.

## Naming Convention Enforcement
- Test file: `test_<feature>_<scenario>.py`
- Test method: `test_<scenario>()`
- Marker enforcement:
  - Web tests: exactly 1 feature marker (`chat|file|prompt`) + exactly 1 suite marker (`smoke|regression|sanity`)

Examples:
- `test_chat_send_message.py`
- `test_file_upload_success.py`
- `test_prompt_search_and_apply.py`

## Feature-based Routing Rules
- `chat` → `tests/web/chat`
- `file` → `tests/web/file_handling`
- `prompt` → `tests/web/prompt_library`
- unclear feature → ask clarification before generating

Interactive generator:
```bash
python -m utils.interactive_test_generator
```

Locator guard:
```bash
python -m utils.locator_guard
```

Policy guard (pre-run validation for naming + markers + locator errors):
```bash
python -m utils.policy_guard
```

It asks:
- feature
- test type (`web`)
- scenario
- test data JSON (optional)
- suite tag (`smoke/regression/sanity`)

## Branch Strategy and PR Workflow
Recommended branch model:
- `main`: production-ready baseline
- `develop`: active integration branch
- `feature/<name>`: feature/test additions
- `bugfix/<name>`: bug fixes

PR workflow:
1. Create branch from `develop`
2. Implement changes + tests
3. Raise PR to `develop`
4. Mandatory review and CI pass
5. Squash merge
6. Promote to `main` by release PR

## Notes
- Browser policy: **Chromium only**
- Playwright mode: **sync**
- UI tests must not contain inline locators (POM only)

