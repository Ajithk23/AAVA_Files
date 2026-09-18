# GitHub Copilot Instructions — DocuChat Test Framework

## Parametrization Standard (MANDATORY)

When creating new test cases that share identical test steps but differ only by
**model name** (e.g. "5 CRT", "5-mini CRT", "4.1 mini CRT") or **chat type**,
you MUST use `pytest.mark.parametrize`. Do NOT create separate files per model variant.

### Rules

1. **One file per scenario group** — group by what the test does (e.g. Chat with Documents
   Initialization, Document Review Initialization, Code Assistant Python). The filename
   must reflect the scenario and TC number range, e.g.:
   `test_tc004_tc005_tc006_chat_initialization_chat_with_documents.py`

2. **Model variants list at the top** — define all variants using `pytest.param`:
   ```python
   _MODEL_VARIANTS = [
       pytest.param("5-mini CRT", "TC004", "tc004", id="TC004"),
       pytest.param("5 CRT",      "TC005", "tc005", id="TC005"),
       pytest.param("4.1 mini CRT","TC006","tc006", id="TC006"),
   ]
   ```
   Each `pytest.param` must include: `(model_name, tc_name, tc_key, id=tc_key_upper)`.

3. **Single `_run_tc_flow` function** — one shared async function accepts
   `model_name`, `tc_name`, `tc_key` (and `file_prefix` if file selection is needed).
   No per-TC copies.

4. **Single parametrized test function** — decorated with both marks and parametrize:
   ```python
   @pytest.mark.chat
   @pytest.mark.regression
   @pytest.mark.parametrize("model_name, tc_name, tc_key", _MODEL_VARIANTS)
   async def test_chat_initialization_chat_with_documents(docuchat_context, model_name, tc_name, tc_key):
       _td = _get_chat_inputs(tc_key)
       await _run_tc_flow(docuchat_context, query=_td.query, tc_name=tc_name,
                          model_name=model_name, tc_key=tc_key)
   ```

5. **TC traceability is preserved** — `tc_key` (e.g. "tc004") is passed to
   `_get_chat_inputs`, `_verify_long_query_response`, and `_run_tc_flow` so that
   qTest integration, screenshot naming, and log tagging all reference the correct TC number.
   The `id=` in `pytest.param` ensures terminal/report output shows `[TC004]`, `[TC005]` etc.

6. **Adding a new model** — add ONE `pytest.param` line to `_MODEL_VARIANTS`. No other
   changes needed anywhere in the file.

7. **`if __name__ == "__main__"` block** — always include at the bottom for direct execution:
   ```python
   if __name__ == "__main__":
       raise SystemExit(pytest.main([__file__, "--env=qa", "--headless=false", "-vv", "-s"]))
   ```

## File Naming Convention

| Scenario | File name pattern |
|---|---|
| Chat Initialization — Chat with Documents | `test_tc{X}_tc{Y}_tc{Z}_chat_initialization_chat_with_documents.py` |
| Chat Initialization — Document Review | `test_tc{X}_tc{Y}_tc{Z}_chat_initialization_document_review.py` |
| Chat Initialization — Code Assistant Python | `test_tc{X}_tc{Y}_tc{Z}_chat_initialization_code_assistant_python.py` |
| Document Validations — Chat with Documents | `test_tc{X}_tc{Y}_tc{Z}_document_validations_chat_with_documents.py` |

## Existing Parametrized Groups (reference)

| File | TCs | Models |
|---|---|---|
| `test_tc004_tc005_tc006_chat_initialization_chat_with_documents.py` | TC004, TC005, TC006 | 5-mini CRT, 5 CRT, 4.1 mini CRT |
| `test_tc007_tc008_tc009_chat_initialization_document_review.py` | TC007, TC008, TC009 | 5-mini CRT, 5 CRT, 4.1 mini CRT |
| `test_tc010_tc011_tc012_chat_initialization_code_assistant_python.py` | TC010, TC011, TC012 | 5-mini CRT, 5 CRT, 4.1 mini CRT |
| `test_tc013_tc014_tc015_document_validations_chat_with_documents.py` | TC013, TC014, TC015 | 5.1 mini CRT, 5 CRT, 4.1 mini CRT |

## General Coding Standards

- All test files use `async def` with `pytest_asyncio` (already configured in `pytest.ini`).
- Import helpers from `tests.web.chat.chat_test_helpers` — do not duplicate helper logic.
- Use `_run_step` from `utils.step_runner` for every test step — never call page actions directly
  in the test function body.
- Screenshots and qTest defect submission are handled automatically by `conftest.py` on failure.
- Never hardcode `base_url` or `timeout_ms` — always read from `docuchat_context["settings"]`.
