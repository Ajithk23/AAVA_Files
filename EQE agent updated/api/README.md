# API Test Framework

This API layer is separate from the existing Playwright UI framework and is designed to run in the same pytest project without modifying current UI tests.

## Principles

- Keep reusable API framework code under `api/`.
- Keep all API test files under `tests/api/`, preserving scenario folders there when needed.
- Never hardcode `Authorization`, `Application`, `Cs-Client-Principal`, or base URLs.
- Read runtime values from `.env` first, then fall back to existing `config/config.yaml` environment selection for `timeout_ms` and `verify_ssl`.
- Build headers in one place only.
- Route all requests through `ApiClient` for reuse, retries, logging, and consistent failures.

## Ownership

- `api/` contains shared API framework code only: client, config, headers, validators, and services.
- `tests/api/` is the single home for API testcase creation, feature-wise testcase folders, and pytest collection.
- Do not add testcase modules under `api/`.

## UI Host vs API Host

- The UI framework base URL is controlled by `config/config.yaml` and is used by Playwright web tests.
- The API framework base URL should be controlled separately through `API_BASE_URL` in `.env`.
- Do not point `API_BASE_URL` to the UI host unless the API is actually served from the same host.

Example for INT:

```env
# UI host used by web tests
# config/config.yaml -> https://csgpt.int.ai.caresource.corp/

# API host used by API tests
API_BASE_URL=https://api.int.ai.caresource.corp/
```

## Supported environment variables

- `API_BASE_URL` for API tests
- `BASE_URL` only as a fallback when an API-specific base URL is not provided
- `API_APPLICATION` or `APPLICATION`
- `API_CS_CLIENT_PRINCIPAL` or `CS_CLIENT_PRINCIPAL`
- `API_AUTHORIZATION` or `AUTHORIZATION` or `API_BEARER_TOKEN`
- `API_PROFILE=enterprise` to switch the loader to `ENTERPRISE_API_*` values
- `ENTERPRISE_API_BASE_URL`, `ENTERPRISE_API_APPLICATION`, `ENTERPRISE_API_CS_CLIENT_PRINCIPAL`, `ENTERPRISE_API_AUTHORIZATION`

## Example `.env`

```env
API_BASE_URL=https://api.int.ai.caresource.corp/
API_APPLICATION=your-application-value
API_CS_CLIENT_PRINCIPAL=your-client-principal-value
API_AUTHORIZATION=Bearer your-token-if-required

ENTERPRISE_API_BASE_URL=https://api.int.ai.caresource.corp/enterprise/docs/v1/swagger/#/
ENTERPRISE_API_APPLICATION=your-application-value
ENTERPRISE_API_CS_CLIENT_PRINCIPAL=your-client-principal-value
ENTERPRISE_API_AUTHORIZATION=Bearer your-token-if-required
```

Select the Enterprise profile by setting:

```env
API_PROFILE=enterprise
```

## pytest usage

Run API-only unit coverage:

```powershell
pytest tests/api -vv
```

Run API tests against INT settings:

```powershell
pytest tests/api -vv --env=int
```

The dedicated fixture in `tests/api/conftest.py` skips live API execution when required `.env` values are missing, so existing UI runs remain unaffected.

Example test layout:

```text
tests/api/
	conftest.py
	test_api_framework_smoke.py
	INT_API_TESTCASES/
		test_tc_01_api_int_get_chat_thread.py
		chat_threads/
			test_tc_02_api_int_get_chat_thread_by_id.py
```

## API history filtering

The cumulative API history file is written to `Test_Latest_Run_Details/API-INT_Latest_Run/api_execution_history.json`.

Use the helper script below to filter it from the terminal:

```powershell
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --latest
```

Examples:

```powershell
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --date 2026-04-30
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --start-date 04-29-2026 --end-date 04-30-2026
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --status PASSED
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --test-case TC_01
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --endpoint /docu_chat/v1/chat_threads/
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --status PASSED --latest --json
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --date 2026-04-30 --stats
c:/Users/cs221014/AIDev-testing/.venv/Scripts/python.exe scripts/filter_api_history.py --start-date 04-29-2026 --end-date 04-30-2026 --stats
```