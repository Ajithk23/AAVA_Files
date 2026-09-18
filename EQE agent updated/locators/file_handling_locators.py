FILE_HANDLING_LOCATORS = {
    "upload_input": [
        {"strategy": "data-testid", "value": "file-upload-input"},
        {"strategy": "role", "value": "textbox|Upload"},
        {"strategy": "css", "value": "input[type='file']"},
        {"strategy": "relative", "value": "section input[type='file']"},
        {"strategy": "xpath", "value": "//input[@type='file']"},
    ],
    "upload_button": [
        {"strategy": "data-testid", "value": "upload-button"},
        {"strategy": "role", "value": "button|Upload"},
        {"strategy": "text", "value": "Upload"},
        {"strategy": "css", "value": "button:has-text('Upload')"},
        {"strategy": "xpath", "value": "//button[contains(.,'Upload')]"},
    ],
    "uploaded_file_row": [
        {"strategy": "data-testid", "value": "file-row"},
        {"strategy": "css", "value": "[data-testid='file-row']"},
        {"strategy": "relative", "value": "table tbody tr"},
        {"strategy": "xpath", "value": "//table//tbody//tr"},
    ],
}
