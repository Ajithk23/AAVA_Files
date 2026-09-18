from __future__ import annotations

import re

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import Error as PlaywrightError

from locators.chat_locators import CHAT_LOCATORS
from pages.base_page import BasePage
from utils.locator_engine import find_element_with_fallback


class ChatPage(BasePage):
    async def open_new_chat(self) -> None:
        """Click the '➕ New Chat' button to open the chat interface."""
        try:
            element = await find_element_with_fallback(
                self.page, "new_chat_button",
                CHAT_LOCATORS["new_chat_button"], self.timeout_ms
            )
            await element.click()
            await self.page.wait_for_load_state("domcontentloaded")
        except (AssertionError, PlaywrightTimeoutError):
            # If the button isn't found, chat may already be open
            pass

    async def send_message(self, message: str) -> None:
        """Open new chat, type message and submit by pressing Enter."""
        await self.open_new_chat()
        element = await find_element_with_fallback(
            self.page, "chat_input", CHAT_LOCATORS["chat_input"], self.timeout_ms
        )
        await element.click()
        await element.fill(message)

        current_value = ""
        try:
            current_value = (await element.input_value() or "").strip()
        except Exception:
            current_value = ""

        if current_value != message.strip():
            await self.page.wait_for_timeout(500)
            element = await find_element_with_fallback(
                self.page, "chat_input", CHAT_LOCATORS["chat_input"], self.timeout_ms
            )
            await element.click()
            await element.fill(message)

            try:
                current_value = (await element.input_value() or "").strip()
            except Exception:
                current_value = ""

        if current_value != message.strip():
            raise AssertionError("Chat input did not retain the message before submit")

        # Prefer clicking Send when available; Enter remains a fallback for compatibility.
        send_candidates = [
            self.page.locator("button[data-testid='stChatInputSubmitButton']").first,
            self.page.get_by_role("button", name=re.compile(r"send", re.IGNORECASE)).first,
            self.page.locator("button:has-text('Send')").first,
            self.page.locator("button[aria-label*='Send']").first,
        ]
        sent = False
        for candidate in send_candidates:
            try:
                if await candidate.count() > 0 and await candidate.is_visible() and not await candidate.is_disabled():
                    await candidate.click()
                    sent = True
                    break
            except Exception:
                continue

        if not sent:
            await element.press("Enter")

        try:
            await self.page.wait_for_timeout(300)
        except Exception:
            pass

    async def get_latest_message(self, timeout_ms: int | None = None) -> str:
        """Return the text of the latest chat message bubble."""
        try:
            effective_timeout = timeout_ms if timeout_ms is not None else self.timeout_ms
            assistant_messages = self.page.locator("[data-testid='stChatMessage']")
            message_count = await assistant_messages.count()
            if message_count > 0:
                for index in range(message_count - 1, -1, -1):
                    candidate = assistant_messages.nth(index)
                    try:
                        candidate_text = (await candidate.text_content() or "").strip()
                    except Exception:
                        continue

                    lower_text = candidate_text.lower()
                    if not candidate_text:
                        continue
                    if lower_text in {"thinking...", "thinking", "assistant"}:
                        continue
                    if "regenerate response" in lower_text and len(candidate_text) < 40:
                        continue
                    return candidate_text

            element = await find_element_with_fallback(
                self.page, "latest_message", CHAT_LOCATORS["latest_message"], effective_timeout
            )
            return await element.text_content() or ""
        except (AssertionError, PlaywrightTimeoutError, PlaywrightError):
            return ""
