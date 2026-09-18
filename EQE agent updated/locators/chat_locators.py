CHAT_LOCATORS = {
    "new_chat_button": [
        {"strategy": "text", "value": "➕ New Chat"},
        {"strategy": "css", "value": "button:has-text('New Chat')"},
        {"strategy": "xpath", "value": "//*[contains(text(),'New Chat')]"},
    ],
    "chat_input": [
        {"strategy": "css", "value": "textarea[placeholder='How can I help?']"},
        {"strategy": "css", "value": "textarea[placeholder*='help']"},
        {"strategy": "css", "value": "textarea[placeholder*='Help']"},
        {"strategy": "css", "value": "main textarea"},
        {"strategy": "xpath", "value": "//textarea[contains(@placeholder,'help')]"},
    ],
    "latest_message": [
        {"strategy": "css", "value": "[data-testid='stChatMessage']:last-child"},
        {"strategy": "css", "value": "[data-testid='stChatMessageContent']:last-child"},
        {"strategy": "css", "value": "[data-testid='stChatMessageContent'] [data-testid='stMarkdownContainer']:last-child"},
        {"strategy": "css", "value": "[data-testid='stChatMessage'] [data-testid='stMarkdownContainer']:last-child"},
        {"strategy": "css", "value": "[data-testid='stMarkdownContainer'] p:last-child"},
        {"strategy": "css", "value": ".stChatMessage:last-child"},
        {"strategy": "css", "value": "[class*='assistant']:last-child"},
        {"strategy": "css", "value": "[data-testid='assistant-message']:last-child"},
        {"strategy": "xpath", "value": "(//*[contains(@data-testid,'ChatMessage')])[last()]"},
    ],
    "copy_response_button": [
        {"strategy": "css", "value": "button[aria-label*='copy' i]"},
        {"strategy": "css", "value": "button[title*='copy' i]"},
        {"strategy": "css", "value": "button[data-testid*='copy' i]"},
        # Streamlit standard: aria-label="Copy to clipboard"
        {"strategy": "css", "value": "button[aria-label='Copy to clipboard']"},
        {"strategy": "css", "value": "button[aria-label*='clipboard' i]"},
        # Streamlit data-testid patterns for copy button
        {"strategy": "css", "value": "[data-testid='stCopyButton']"},
        {"strategy": "css", "value": "[data-testid='stChatMessageActionsCopyButton']"},
        # Non-button copy icons (Streamlit may use span/div with click handler)
        {"strategy": "css", "value": "[data-testid*='copy' i]"},
        {"strategy": "css", "value": "[aria-label*='copy' i]"},
        {"strategy": "css", "value": "[title*='copy' i]"},
        {"strategy": "xpath", "value": "//button[contains(translate(@aria-label,'COPY','copy'),'copy')]"},
        {"strategy": "xpath", "value": "//*[contains(@class,'copy')]//button"},
        {"strategy": "css", "value": "[data-testid='stChatMessage']:last-child button[aria-label*='copy' i]"},
        {"strategy": "css", "value": "[data-testid='stChatMessage']:last-child button[aria-label*='clipboard' i]"},
    ],
    "regenerate_response_button": [
        {"strategy": "css", "value": "button:has-text('Regenerate Response')"},
        {"strategy": "css", "value": "button:has-text('Regenerate')"},
        {"strategy": "xpath", "value": "//button[contains(translate(normalize-space(),'REGENERATE','regenerate'),'regenerate')]"},
        {"strategy": "css", "value": "[data-testid*='regenerate']"},
        {"strategy": "css", "value": "button[aria-label*='regenerate' i]"},
    ],
}
