"""TC042 Regression - CareSource GPT Prompt Library with 5 CRT and Basic Chat.

Test Case Name : TC042_Regression_CareSource GPT_Prompt Library_Validate user level Prompt addition,
                 edit and delete functionality using model 5 CRT with Basic chat
"""

import pytest

from tests.web.regression.prompt_library.prompt_library_case_runner import run_prompt_library_case


@pytest.mark.prompt
@pytest.mark.regression
async def test_tc042_regression_caresource_gpt_prompt_library_validate_user_level_prompt_addition_edit_and_delete_functionality_using_model_5crt_with_basic_chat(
    docuchat_context,
):
    await run_prompt_library_case(
        docuchat_context=docuchat_context,
        tc_key="tc042",
        tc_name="TC042",
        include_delete=True,
    )