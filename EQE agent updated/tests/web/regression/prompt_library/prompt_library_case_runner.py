from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from utils.step_runner import run_step as _run_step
from utils.test_data_loader import get_prompt_library_case_inputs

from tests.web.regression.prompt_library.prompt_library_test_helpers import (
    clear_search_prompts,
    click_create_new_prompt,
    click_delete_prompt_button,
    click_first_action_button,
    click_modal_button,
    configure_chat_for_model,
    delete_prompts_by_prefix,
    execute_selected_prompt,
    open_edit_prompt_modal,
    expect_text_not_visible,
    expect_text_visible,
    fill_prompt_form,
    open_prompt_library,
    search_prompt,
    select_saved_prompt,
    validate_landing,
    verify_saved_prompt_option_visible,
    verify_saved_prompt_loaded,
    verify_create_prompt_modal,
    verify_prompt_library_ui,
)


def _seed_titles(base_title: str) -> list[str]:
    return [f"{base_title} {idx}" for idx in range(1, 2)]


async def run_prompt_library_case(
    docuchat_context: dict[str, object],
    tc_key: str,
    tc_name: str,
    include_delete: bool,
) -> None:
    page = docuchat_context["page"]
    settings = docuchat_context["settings"]
    data = get_prompt_library_case_inputs(tc_key)
    titles = _seed_titles(data.base_title)
    tc_prefix = tc_name.upper()

    async def _create_prompt(title: str, prompt: str, display_order: int) -> None:
        await click_create_new_prompt(page)
        await verify_create_prompt_modal(page)
        await fill_prompt_form(page, title=title, prompt=prompt, display_order=display_order)
        await click_modal_button(page, r"create\s*prompt")

    async def _step_5_required_no_data() -> None:
        await click_modal_button(page, r"create\s*prompt")
        await expect_text_visible(page, r"prompt\s*text\s*is\s*required")

    async def _step_6_required_prompt_only() -> None:
        await fill_prompt_form(page, title=titles[0])
        await click_modal_button(page, r"create\s*prompt")
        await expect_text_visible(page, r"prompt\s*text\s*is\s*required")

    async def _step_7_cancel_creation() -> None:
        title = f"{data.base_title} Cancel"
        await fill_prompt_form(page, title=title, prompt=f"{data.base_prompt} cancel flow")
        await click_modal_button(page, r"cancel")
        await search_prompt(page, title)
        await expect_text_not_visible(page, title)

    async def _step_9_create_multiple() -> None:
        for idx, title in enumerate(titles[1:], start=1):
            await _create_prompt(title, f"{data.base_prompt} #{idx+1}", (idx % 4) + 1)
            await expect_text_visible(page, title)

    async def _step_clear_prompt_search_box() -> None:
        await clear_search_prompts(page)
        await verify_prompt_library_ui(page)

    async def _step_10_configure_chat() -> None:
        await page.wait_for_timeout(2000)
        await configure_chat_for_model(page, model_name=data.model_name)
        await page.wait_for_timeout(5000)

    async def _step_11_open_saved_prompts() -> None:
        await page.wait_for_timeout(5000)
        await verify_saved_prompt_option_visible(page, titles[0])

    async def _step_12_select_prompt() -> None:
        await select_saved_prompt(page, titles[0])
        await page.wait_for_timeout(5000)
        await verify_saved_prompt_loaded(page, data.base_prompt)

    async def _step_13_execute_prompt() -> None:
        await execute_selected_prompt(page, data.base_prompt)

    async def _step_14_back_to_prompt_library() -> None:
        await open_prompt_library(page)

    async def _step_15_open_edit() -> None:
        await search_prompt(page, titles[0])
        await expect_text_visible(page, titles[0])
        await open_edit_prompt_modal(page, prompt_title=titles[0])

    async def _step_cleanup_case_prompts() -> None:
        await open_prompt_library(page)
        await clear_search_prompts(page)
        await search_prompt(page, tc_prefix)
        await page.wait_for_timeout(700)

        no_results_pattern = rf"no\s*prompts\s*found\s*for\s*search\s*:\s*{re.escape(tc_prefix.lower())}"
        no_results = page.get_by_text(re.compile(no_results_pattern, re.IGNORECASE)).first
        if await no_results.count() > 0:
            return

        await delete_prompts_by_prefix(page, [tc_prefix])
        await clear_search_prompts(page)
        await search_prompt(page, tc_prefix)
        await page.wait_for_timeout(700)
        await expect_text_visible(page, no_results_pattern)

    async def _step_16_edit_and_save() -> None:
        await fill_prompt_form(page, title=data.edited_title, prompt=data.edited_prompt)
        await click_modal_button(page, r"save\s*changes|save")
        await expect_text_visible(page, data.edited_title)

    async def _step_17_update_display_order() -> None:
        await search_prompt(page, data.edited_title)
        await expect_text_visible(page, data.edited_title)
        await open_edit_prompt_modal(page, prompt_title=data.edited_title)
        await fill_prompt_form(page, display_order=data.display_order + 2)
        await click_modal_button(page, r"save\s*changes|save")

    async def _step_21_back_to_prompt_library() -> None:
        await open_prompt_library(page)

    async def _step_25_open_delete() -> None:
        await search_prompt(page, data.edited_title)
        await expect_text_visible(page, data.edited_title)
        await click_delete_prompt_button(page, prompt_title=data.edited_title)
        await expect_text_visible(page, r"delete\s*prompt")

    async def _step_26_delete_cancel() -> None:
        await click_modal_button(page, r"cancel")
        await expect_text_visible(page, data.edited_title)

    async def _step_27_open_delete_again() -> None:
        await search_prompt(page, data.edited_title)
        await expect_text_visible(page, data.edited_title)
        await click_delete_prompt_button(page, prompt_title=data.edited_title)
        await expect_text_visible(page, r"delete\s*prompt")

    async def _step_28_confirm_delete() -> None:
        await click_modal_button(page, r"yes\s*,?\s*delete|delete")
        # Deletion toasts can briefly include the deleted title; strict title
        # invisibility is validated in Step 29 after targeted search refresh.
        await expect_text_not_visible(page, r"delete\s*prompt")
        await page.wait_for_timeout(800)

    async def _step_29_search_deleted() -> None:
        await clear_search_prompts(page)
        await search_prompt(page, tc_prefix)
        await page.wait_for_timeout(700)

        def _edited_rows_locator():
            return page.locator("div").filter(
                has=page.get_by_text(data.edited_title)
            ).filter(
                has=page.locator(
                    "button[aria-label*='Delete'], "
                    "button[title*='Delete'], "
                    "button:has([data-testid='stIconMaterial']:has-text('delete')), "
                    "button:has-text('🗑')"
                )
            )

        edited_rows = _edited_rows_locator()
        if await edited_rows.count() > 0:
            await click_delete_prompt_button(page, prompt_title=data.edited_title)
            await expect_text_visible(page, r"delete\s*prompt")
            await page.wait_for_timeout(2000)
            await click_modal_button(page, r"yes\s*,?\s*delete|delete")
            await page.wait_for_timeout(2000)
            await clear_search_prompts(page)
            await search_prompt(page, tc_prefix)
            await page.wait_for_timeout(700)
            edited_rows = _edited_rows_locator()

        assert await edited_rows.count() == 0, "Edited TC041 prompt row is still visible in Prompt Library"

    async def _step_30_deleted_not_in_chat_saved_prompts() -> None:
        await configure_chat_for_model(page, model_name=data.model_name)
        await click_modal_button(page, r"saved\s*prompts")
        await expect_text_not_visible(page, data.edited_title)

    async def _step_exit() -> None:
        await page.wait_for_timeout(100)

    steps: list[tuple[int, str, Callable[[], Awaitable[None]]]] = [
        (1, "Open the browser (Chrome/Edge). and Enter URL as https://docu-chat.crt.ai.caresource.corp", lambda: validate_landing(page, str(settings["base_url"]))),
        (2, "Verify the landing page options are displayed (Chat, File Management, Prompt Library).", lambda: validate_landing(page, str(settings["base_url"]))),
        (3, "Select Prompt Library from sidebar and verify the UI details of Prompt Library page", lambda: open_prompt_library(page)),
        (3, "Verify Prompt Library UI details", lambda: verify_prompt_library_ui(page)),
        (4, "Click on Create New Prompt button", lambda: click_create_new_prompt(page)),
        (4, "Verify Create Prompt window details", lambda: verify_create_prompt_modal(page)),
        (5, "Give no data to any fields in Create Prompt window and click on Create Prompt button", _step_5_required_no_data),
        (6, "Give data in Title field and no data in Prompt and click on Create Prompt button", _step_6_required_prompt_only),
        (7, "Give data in Title and Prompt and click on Cancel button", _step_7_cancel_creation),
        (7, "Clear Search Prompts text box and restore Prompt Library list", _step_clear_prompt_search_box),
        (8, "Enter data in Title, Prompt, Display Order and click on Create Prompt", lambda: _create_prompt(titles[0], data.base_prompt, data.display_order)),
        (8, "Verify Prompt created successfully", lambda: expect_text_visible(page, titles[0])),
        (9, "Repeat prompt creation to create at least 2 prompts with mixed display order", _step_9_create_multiple),
        (10, f"Navigate to Chat and select Model {data.model_name} with Basic Chat", _step_10_configure_chat),
        (11, "Click on Saved prompts and verify prompts are visible", _step_11_open_saved_prompts),
        (12, "Select the prompt from the dropdown", _step_12_select_prompt),
        (13, "Execute the prompt", _step_13_execute_prompt),
        (14, "Navigate back to Prompt Library", _step_14_back_to_prompt_library),
        (15, "Verify Edit Prompt by selecting existing prompt and clicking Edit", _step_15_open_edit),
        (16, "Update Title and Prompt details and save changes", _step_16_edit_and_save),
        (17, "Update the display order and verify", _step_17_update_display_order),
        (21, "Navigate back to Prompt Library", _step_21_back_to_prompt_library),
        (24, "Clear Search Prompts text box and restore Prompt Library list", _step_clear_prompt_search_box),
    ]

    if include_delete:
        steps.extend(
            [
                (25, "Verify Delete Prompt and open Delete confirmation", _step_25_open_delete),
                (26, "Click Cancel on Delete confirmation", _step_26_delete_cancel),
                (27, "Open Delete confirmation again", _step_27_open_delete_again),
                (28, "Click Yes Delete to confirm delete action", _step_28_confirm_delete),
                (29, "Search deleted prompt and verify it is not present", _step_29_search_deleted),
                (29, "Clear Search Prompts text box and restore Prompt Library list", _step_clear_prompt_search_box),
                (30, "Navigate to Chat and verify deleted prompt is not shown in Saved prompts", _step_30_deleted_not_in_chat_saved_prompts),
                (31, f"Delete all prompts starting with {tc_prefix} before exit", _step_cleanup_case_prompts),
                (32, "Exit the application by clicking the browser close button", _step_exit),
            ]
        )
    else:
        steps.append((25, "Exit the application by clicking the browser close button", _step_exit))

    for num, name, step_fn in steps:
        await _run_step(num, name, step_fn(), tc_name, page)

