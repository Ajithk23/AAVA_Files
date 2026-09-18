from __future__ import annotations

from locators.file_handling_locators import FILE_HANDLING_LOCATORS
from pages.base_page import BasePage


class FileHandlingPage(BasePage):
    async def upload_file(self, file_path: str) -> None:
        await self.set_input_files("upload_input", FILE_HANDLING_LOCATORS, file_path)
        await self.click("upload_button", FILE_HANDLING_LOCATORS)

    async def has_uploaded_row(self) -> bool:
        return bool(await self.text_content("uploaded_file_row", FILE_HANDLING_LOCATORS))
