# DocuChat QA Framework — Developer Convenience Makefile
# Usage: make <target>
#
# Prerequisites: GNU Make installed (scoop install make  OR  choco install make)
# On Windows PowerShell, prefer using the PowerShell scripts in scripts/

PYTHON   := .venv/Scripts/python.exe
PYTEST   := .venv/Scripts/pytest.exe
PIP      := .venv/Scripts/pip.exe
ENV      ?= qa

.PHONY: help install test smoke regression sanity report dashboard schedule \
        generate policy-check lint clean venv

## help: Show this help message
help:
	@grep -E '^##' $(MAKEFILE_LIST) | sed 's/## //'

## venv: Create virtual environment
venv:
	python -m venv .venv

## install: Install all dependencies into .venv
install: venv
	$(PIP) install -r requirements.txt
	$(PYTHON) -m playwright install chromium

## policy-check: Run policy guard before any test execution
policy-check:
	$(PYTHON) -m utils.policy_guard

## test: Run ALL tests (env=qa by default, override: make test ENV=uat)
test: policy-check
	$(PYTHON) run_tests.py --env=$(ENV)

## smoke: Run smoke-tagged tests only
smoke: policy-check
	$(PYTEST) -m smoke --env=$(ENV) -v

## regression: Run regression-tagged tests only
regression: policy-check
	$(PYTEST) -m regression --env=$(ENV) -v

## sanity: Run sanity-tagged tests only
sanity: policy-check
	$(PYTEST) -m sanity --env=$(ENV) -v

## chat: Run chat feature tests only
chat: policy-check
	$(PYTEST) tests/web/chat --env=$(ENV) -v

## file: Run file handling feature tests only
file: policy-check
	$(PYTEST) tests/web/file_handling --env=$(ENV) -v

## prompt: Run prompt library feature tests only
prompt: policy-check
	$(PYTEST) tests/web/prompt_library --env=$(ENV) -v

## report: Open Allure report (requires Allure CLI)
report:
	allure serve reports/allure-results

## dashboard: Launch Streamlit QA dashboard
dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py --server.port=8501 --server.headless=true --server.runOnSave=false --browser.gatherUsageStats=false --server.fileWatcherType=none

## schedule: Start the recurring test scheduler
schedule:
	$(PYTHON) run_scheduler.py

## generate: Launch interactive AI test generator
generate:
	$(PYTHON) -m utils.interactive_test_generator

## history: Print run history summary to terminal
history:
	$(PYTHON) run_history_report.py

## lint: Basic check that all test files conform to naming policy
lint:
	$(PYTHON) -m utils.policy_guard

## clean: Remove compiled bytecode, caches, and old reports
clean:
	@if exist .pytest_cache rmdir /s /q .pytest_cache 2>nul; true
	@if exist __pycache__ rmdir /s /q __pycache__ 2>nul; true
	@for /r %%d in (__pycache__) do @rmdir /s /q "%%d" 2>nul; true
	@if exist reports\allure-results rmdir /s /q reports\allure-results 2>nul; true
	@if exist reports\archive rmdir /s /q reports\archive 2>nul; true
	@echo Clean complete.
