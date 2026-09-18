PROMPT_LIBRARY_LOCATORS = {
    "search_input": [
        {"strategy": "data-testid", "value": "prompt-search"},
        {"strategy": "role", "value": "textbox|Search prompts"},
        {"strategy": "text", "value": "Search"},
        {"strategy": "css", "value": "input[placeholder*='Search']"},
        {"strategy": "xpath", "value": "//input[contains(@placeholder,'Search')]"},
    ],
    "prompt_card": [
        {"strategy": "data-testid", "value": "prompt-card"},
        {"strategy": "css", "value": "[data-testid='prompt-card']"},
        {"strategy": "relative", "value": "section article"},
        {"strategy": "xpath", "value": "//article[contains(@class,'prompt')]"},
    ],
    "apply_prompt_button": [
        {"strategy": "data-testid", "value": "apply-prompt"},
        {"strategy": "role", "value": "button|Apply"},
        {"strategy": "text", "value": "Apply"},
        {"strategy": "css", "value": "button:has-text('Apply')"},
        {"strategy": "xpath", "value": "//button[contains(.,'Apply')]"},
    ],
}
