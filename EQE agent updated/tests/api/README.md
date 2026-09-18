# API Tests

`tests/api/` is the single home for API testcase creation and feature-wise testcase organization.

## Layout

- `INT_API_TESTCASES/` for INT API tests
- `ENTERPRISE_API_TESTCASES/` for Enterprise API tests
- Feature folders live under the environment-specific testcase tree

## Rule

- Put shared framework code in `api/`
- Put all pytest testcase files in `tests/api/`
- Do not duplicate testcase modules under `api/`