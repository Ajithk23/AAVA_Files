from __future__ import annotations

from locators.prompt_library_locators import PROMPT_LIBRARY_LOCATORS
from pages.base_page import BasePage


class PromptLibraryPage(BasePage):
    async def search_prompt(self, text: str) -> None:
        await self.fill("search_input", PROMPT_LIBRARY_LOCATORS, text)

    async def apply_first_prompt(self) -> None:
        await self.click("apply_prompt_button", PROMPT_LIBRARY_LOCATORS)

    async def has_prompt_card(self) -> bool:
        return bool(await self.text_content("prompt_card", PROMPT_LIBRARY_LOCATORS))
