from __future__ import annotations

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from utils.locator_engine import find_element_with_fallback
from utils.retry import async_retry


class BasePage:
    def __init__(self, page: Page, timeout_ms: int = 15000) -> None:
        self.page = page
        self.timeout_ms = timeout_ms

    async def open(self, url: str) -> None:
        await self.page.goto(url)

    @async_retry(max_attempts=3, delay_sec=0.5, exceptions=(PlaywrightTimeoutError, AssertionError))
    async def click(self, locator_key: str, locator_map: dict) -> None:
        element = await find_element_with_fallback(self.page, locator_key, locator_map[locator_key], self.timeout_ms)
        await element.click()

    @async_retry(max_attempts=3, delay_sec=0.5, exceptions=(PlaywrightTimeoutError, AssertionError))
    async def fill(self, locator_key: str, locator_map: dict, value: str) -> None:
        element = await find_element_with_fallback(self.page, locator_key, locator_map[locator_key], self.timeout_ms)
        await element.fill(value)

    async def text_content(self, locator_key: str, locator_map: dict) -> str:
        element = await find_element_with_fallback(self.page, locator_key, locator_map[locator_key], self.timeout_ms)
        return await element.text_content() or ""

    async def set_input_files(self, locator_key: str, locator_map: dict, file_path: str) -> None:
        element = await find_element_with_fallback(self.page, locator_key, locator_map[locator_key], self.timeout_ms)
        await element.set_input_files(file_path)

    async def is_visible(self, locator_key: str, locator_map: dict, timeout_ms: int | None = None) -> bool:
        """Return True if the element is visible within the timeout; False otherwise."""
        try:
            element = await find_element_with_fallback(
                self.page, locator_key, locator_map[locator_key], timeout_ms or self.timeout_ms
            )
            return await element.is_visible()
        except (PlaywrightTimeoutError, AssertionError):
            return False

    async def wait_for_url(self, pattern: str, timeout_ms: int | None = None) -> None:
        await self.page.wait_for_url(pattern, timeout=timeout_ms or self.timeout_ms)
