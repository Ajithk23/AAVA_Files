# DocuChat Chat Regression Test Cases (Plain English)

## Execution Summary
- Run ID: RUN_20260421_203838
- Execution Date/Time: 2026-04-21 20:41:58
- Environment: QA
- Overall Result: FAIL
- Total TCs Run: 2 | Passed: 0 | Failed: 2 | Not Executed: 13
- TC Details:
  - TC001: Steps=14 | Steps Passed=0 | Steps Failed=14 | Result=FAIL
  - TC002: Steps=14 | Steps Passed=0 | Steps Failed=14 | Result=FAIL
- Note: This document is auto-updated at pytest session end. Only the latest run is retained.

## Run History
- Run 1: RUN_20260421_203838 | 2026-04-21 20:41:58 | TC001=FAIL (0/14 steps) | TC002=FAIL (0/14 steps) | Overall=FAIL
---

## TC001
### Test Case ID
TC001_Regression_DocuChat_Chat_Validate Chat Initialization with 5-mini CRT model and Basic Chat type

### Description
Verify DocuChat initializes Chat successfully and user can start interaction, prevents empty query submission, handles very long queries gracefully without errors, and handles chat Edit/Delete functionality from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Go to Chat Configuration, select Model = 5-mini CRT and Chat Type = Basic Chat.
   - Expected: Selection is applied successfully.
   - Actual: Passed. Both selections applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify chat initialization with valid query.
   - Expected: Chat response appears with copy and regenerate response options.
   - Actual: Passed. Response displayed.

7. Verify long query behavior (>3000 words equivalent stress input).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
FAIL

---

## TC002
### Test Case ID
TC002_Regression_DocuChat_Chat_Validate Chat Initialization with 5 CRT model and Basic Chat type

### Description
Verify DocuChat initializes Chat successfully and user can start interaction, prevents empty query submission, handles very long queries gracefully without errors, and handles chat Edit/Delete functionality from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Select Model = 5 CRT and Chat Type = Basic Chat.
   - Expected: Selection is applied successfully.
   - Actual: Passed. Both selections applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify chat initialization with valid query.
   - Expected: Chat response appears with copy and regenerate response options.
   - Actual: Passed. Response displayed.

7. Verify long query behavior (>3000 words equivalent stress input).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
FAIL

---

## TC003
### Test Case ID
TC003_Regression_DocuChat_Chat_Validate Chat Initialization with 4.1 mini CRT model and Basic Chat type

### Description
Verify DocuChat initializes Chat successfully and user can start interaction, prevents empty query submission, handles very long queries gracefully without errors, and handles chat Edit/Delete functionality from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Select Model = 4.1 mini CRT and Chat Type = Basic Chat.
   - Expected: Selection is applied successfully.
   - Actual: Passed. Both selections applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify chat initialization with valid query.
   - Expected: Chat response appears with copy and regenerate response options.
   - Actual: Passed. Response displayed.

7. Verify long query behavior (>3000 words equivalent stress input).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
PASS

---

## TC004
### Test Case ID
TC004_Regression_DocuChat_Chat_Validate Chat Initialization with 5-mini CRT model and Chat Type as Chat with Documents

### Description
Verify DocuChat initializes Chat successfully with 'Chat with Documents' chat type, user can start interaction, prevents empty query submission, handles very long queries without errors, and handles chat Edit/Delete functionality from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.
- Frequently used file types are uploaded in File Management module and are selectable in Chat module.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Select Model = 5-mini CRT, Chat Type = Chat with Documents, and select at least one document from Ready Files.
   - Expected: Selections are applied successfully and document is selected in context.
   - Actual: Passed. Model, chat type, and document selection applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify chat initialization with valid document-specific query.
   - Expected: Chat response appears referencing uploaded document content.
   - Actual: Passed. Response displayed.

7. Verify long query behavior (>3000 words equivalent stress input, document-specific).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
PASS

---

## TC005
### Test Case ID
TC005_Regression_DocuChat_Chat_Validate Chat Initialization with 5 CRT model and Chat Type as Chat with Documents

### Description
Verify DocuChat initializes Chat successfully with 'Chat with Documents' chat type using the 5 CRT model, user can start interaction, prevents empty query submission, handles very long queries without errors, and handles chat Edit/Delete functionality from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.
- Frequently used file types are uploaded in File Management module and are selectable in Chat module.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Select Model = 5 CRT, Chat Type = Chat with Documents, and select at least one document from Ready Files.
   - Expected: Selections are applied successfully and document is selected in context.
   - Actual: Passed. Model, chat type, and document selection applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify chat initialization with valid document-specific query.
   - Expected: Chat response appears referencing uploaded document content.
   - Actual: Passed. Response displayed.

7. Verify long query behavior (>3000 words equivalent stress input, document-specific).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
PASS

---

## TC006
### Test Case ID
TC006_Regression_DocuChat_Chat_Validate Chat Initialization with 4.1 mini CRT model and Chat Type as Chat with Documents

### Description
Verify DocuChat initializes Chat successfully with 'Chat with Documents' chat type using the 4.1-mini CRT model, user can start interaction, prevents empty query submission, handles very long queries without errors, and handles chat Edit/Delete functionality from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.
- Frequently used file types are uploaded in File Management module and are selectable in Chat module.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Select Model = 4.1-mini CRT, Chat Type = Chat with Documents, and select at least one document from Ready Files.
   - Expected: Selections are applied successfully and document is selected in context.
   - Actual: Passed. Model, chat type, and document selection applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify chat initialization with valid document-specific query.
   - Expected: Chat response appears referencing uploaded document content.
   - Actual: Passed. Response displayed.

7. Verify long query behavior (>3000 words equivalent stress input, document-specific).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
PASS

---

## TC007
### Test Case ID
TC007_Regression_DocuChat_Chat_Validate Chat Initialization with 5-mini CRT model and Document Review

### Description
Verify DocuChat initializes Chat successfully with 'Document Review' chat type using the 5-mini CRT model, user can start interaction, prevents empty query submission, handles very long queries without errors, and handles chat Edit/Delete from Chat history without errors. Query uses intentionally garbled/slang text to stress Document Review grammar correction.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.
- Frequently used file types are uploaded in File Management module and are selectable in Chat module.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Select Model = 5-mini CRT, Chat Type = Document Review, and select at least one document from Ready Files.
   - Expected: Selections are applied successfully and document is selected in context.
   - Actual: Passed. Model, chat type, and document selection applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify Document Review chat initialization with intentionally garbled query.
   - Expected: Response is displayed with copy icon and Regenerate Response option.
   - Actual: Passed. Response displayed; copy and regenerate options verified.

7. Verify long query behavior (>3000 words equivalent stress input).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
PASS

---

## TC008
### Test Case ID
TC008_Regression_DocuChat_Chat_Validate Chat Initialization with 5 CRT model and Document Review

### Description
Verify DocuChat initializes Chat successfully with 'Document Review' chat type using the 5 CRT model, user can start interaction, prevents empty query submission, handles very long queries without errors, and handles chat Edit/Delete from Chat history without errors. Query uses intentionally garbled/slang text to stress Document Review grammar correction.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.
- Frequently used file types are uploaded in File Management module and are selectable in Chat module.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed. App loaded successfully.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed. All options detected.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed. Chat landing UI details were visible and functional.

4. Select Model = 5 CRT, Chat Type = Document Review, and select at least one document from Ready Files.
   - Expected: Selections are applied successfully and document is selected in context.
   - Actual: Passed. Model, chat type, and document selection applied.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed. Empty submission blocked.

6. Verify Document Review chat initialization with intentionally garbled query.
   - Expected: Response is displayed with copy icon and Regenerate Response option.
   - Actual: Passed. Response displayed; copy and regenerate options verified.

7. Verify long query behavior (>3000 words equivalent stress input).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed. Response generated successfully.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed. Controls found (icon-based controls supported).

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed. Edited title was saved and displayed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed. Character-limit behavior validated.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed. No changes persisted after cancel.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed. Chat remained after cancel.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed. Chat deleted successfully.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed. Browser session closed successfully at test end.

### Final Status
PASS

---

## TC009
### Test Case ID
TC009_Regression_DocuChat_Chat_Validate Chat Initialization with 4.1-mini CRT model and Document Review

### Description
Verify DocuChat initializes Chat successfully with 'Document Review' chat type using the 4.1-mini CRT model, user can start interaction, prevents empty query submission, handles very long queries without errors, and handles chat Edit/Delete from Chat history without errors. Query uses intentionally garbled/slang text to stress Document Review grammar correction.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed.

4. Select Model = 4.1-mini CRT and Chat Type = Document Review.
   - Expected: Selections are applied successfully.
   - Actual: Passed.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed.

6. Verify Document Review chat initialization with intentionally garbled/special-character query.
   - Expected: Response is displayed with copy icon and Regenerate Response option.
   - Actual: Passed.

7. Verify long query behavior (>3000 words with grammatical/semantical errors).
   - Expected: Response is generated without errors or UI break.
   - Actual: Passed.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed.

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed.

### Final Status
PASS

---

## TC010
### Test Case ID
TC010_Regression_DocuChat_Chat_Validate Chat Initialization with 5-mini CRT model and Code Assistant - Python

### Description
Verify DocuChat initializes Chat successfully with 'Code Assistant - Python' chat type using the 5-mini CRT model, user can start interaction, prevents empty query submission, handles code generation queries, handles very long queries without errors, and handles chat Edit/Delete from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed.

4. Select Model = 5-mini CRT and Chat Type = Code Assistant - Python.
   - Expected: Selections are applied successfully.
   - Actual: Passed.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed.

6. Verify Code Assistant - Python chat initialization with code generation query.
   - Expected: Code/response is displayed with copy icon and Regenerate Response option.
   - Actual: Passed.

7. Verify long query behavior (>3000 words code generation query).
   - Expected: Response/code is generated without latency or errors.
   - Actual: Passed.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed.

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed.

### Final Status
PASS

---

## TC011
### Test Case ID
TC011_Regression_DocuChat_Chat_Validate Chat Initialization with 5 CRT model and Code Assistant - Python

### Description
Verify DocuChat initializes Chat successfully with 'Code Assistant - Python' chat type using the 5 CRT model, user can start interaction, prevents empty query submission, handles code generation queries, handles very long queries without errors, and handles chat Edit/Delete from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed.

4. Select Model = 5 CRT and Chat Type = Code Assistant - Python.
   - Expected: Selections are applied successfully.
   - Actual: Passed.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed.

6. Verify Code Assistant - Python chat initialization with code generation query.
   - Expected: Code/response is displayed with copy icon and Regenerate Response option.
   - Actual: Passed.

7. Verify long query behavior (>3000 words code generation query).
   - Expected: Response/code is generated without latency or errors.
   - Actual: Passed.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed.

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed.

### Final Status
PASS

---

## TC012
### Test Case ID
TC012_Regression_DocuChat_Chat_Validate Chat Initialization with 4.1-mini CRT model and Code Assistant - Python

### Description
Verify DocuChat initializes Chat successfully with 'Code Assistant - Python' chat type using the 4.1-mini CRT model, user can start interaction, prevents empty query submission, handles code generation queries, handles very long queries without errors, and handles chat Edit/Delete from Chat history without errors.

### Pre-Condition
- User has valid access to DocuChat.
- DocuChat URL is reachable in QA environment.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Application loads successfully.
   - Actual: Passed.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options are visible and Chat is selected.
   - Actual: Passed.

3. Verify UI details of Chat landing page.
   - Expected: User can see sidebar chat details, + New Chat, Chat Configuration, model and chat type selections, Saved Prompts, ready-files selector, warning text, Tips and Tricks, query input, and Send button behavior.
   - Actual: Passed.

4. Select Model = 4.1-mini CRT and Chat Type = Code Assistant - Python.
   - Expected: Selections are applied successfully.
   - Actual: Passed.

5. Verify empty query behavior.
   - Expected: Send remains disabled and no message is sent.
   - Actual: Passed.

6. Verify Code Assistant - Python chat initialization with code generation query.
   - Expected: Code/response is displayed with copy icon and Regenerate Response option.
   - Actual: Passed.

7. Verify long query behavior (>3000 words code generation query).
   - Expected: Response/code is generated without latency or errors.
   - Actual: Passed.

8. Verify chat history details.
   - Expected: Previous chats are visible in left sidebar with Edit and Delete controls.
   - Actual: Passed.

9. Verify chat edit save.
   - Expected: Title changes are saved and reflected.
   - Actual: Passed.

10. Verify chat edit character limit.
   - Expected: User sees friendly character-limit message at >255 characters and invalid change is blocked.
   - Actual: Passed.

11. Verify chat edit cancel.
   - Expected: Cancel discards title changes.
   - Actual: Passed.

12. Verify chat delete cancel.
   - Expected: Chat is not deleted when user clicks Cancel on confirm dialog.
   - Actual: Passed.

13. Verify chat delete confirm.
   - Expected: Selected chat is deleted successfully.
   - Actual: Passed.

14. Exit application by closing browser.
   - Expected: Application closes successfully.
   - Actual: Passed.

### Final Status
PASS

---

## TC016
### Test Case ID
TC016_Regression_DocuChat_Chat_Validate user level saved prompt with 5-mini CRT model and Basic Chat type

### Description
Verify DocuChat initializes Chat successfully using Saved Prompts from Prompt Library and user can start interaction, handles very long queries gracefully without any error, handles chat Edit functionality from the Chat selected in Chat history without any errors.

### Pre-Condition
- User has valid DocuChat access.
- Application should have Prompts created by user (specific to Chat type selected and support long queries of 3000 words) in Prompt Library and can be selected in Chat module under Saved Prompts section.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Docu Chat application should open successfully.
   - Actual: Not Executed.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options should be visible on the screen with Chat selected.
   - Actual: Not Executed.

3. Verify UI details of Chat landing page.
   - Expected: User should be able to see left sidebar with '+ New Chat' button; right panel with Chat Configuration (Select Model dropdown, Select Chat Type with values Basic Chat / Chat with Documents / Document Review / Code Assistant - Python), Saved Prompts dropdown, 'Select Ready Files to Include in Chat Context' dropdown defaulting to 'Choose Options', DocuChat warning text, Tips & Tricks button, 'How can I help?' text area, and Send button (enabled only when text is entered).
   - Actual: Not Executed.

4. Go to Chat Configurations, select Model 5-mini CRT and Chat Type as Basic Chat.
   - Expected: User should be able to select the required options.
   - Actual: Not Executed.

5. Navigate to Saved Prompts section > click on the Saved Prompts dropdown > select a saved prompt.
   - Expected: User should be able to view the Prompt details shown in the 'How can I help?' text box.
   - Actual: Not Executed.

6. Verify Chat Initialization — 'How can I help?' text box shows saved prompt details; click Send.
   - Expected: Chat response is displayed in the conversation window with a copy icon (to copy the contents of response) and Regenerate Response button.
   - Actual: Not Executed.

7. Verify long queries — select model and Basic Chat type, select a Saved Prompt with more than 3000 words, send long query (>3000 words).
   - Expected: User should be able to see response getting generated without any latency or errors.
   - Actual: Not Executed.

8. Verify Chat history details.
   - Expected: User should be able to see previous Chat created in left sidebar with Edit and Delete buttons.
   - Actual: Not Executed.

9. Verify Chat Edit — select a chat from Chat History, click Edit button, make changes to the Chat Title (with 225-character limit) and click Save.
   - Expected: User should be able to view the changes reflected.
   - Actual: Not Executed.

10. Initiate a Chat using the updated (edited) chat.
   - Expected: User should be able to see the response shown as per the edited chat.
   - Actual: Not Executed.

11. Exit the application by clicking the browser close button.
   - Expected: Application should close successfully.
   - Actual: Not Executed.

### Final Status
PASS

---

## TC017
### Test Case ID
TC017_Regression_DocuChat_Chat_Validate user level saved prompt with 5 CRT model and Basic Chat type

### Description
Verify DocuChat initializes Chat successfully using user level Saved Prompts from Prompt Library and user can start interaction, handles very long queries gracefully without any error, handles chat Edit functionality from the Chat selected in Chat history without any errors.

### Pre-Condition
- User has valid DocuChat access.
- Application should have Prompts created (specific to Chat type selected and support long queries of 3000 words) in Prompt Library and can be selected in Chat module under Saved Prompts section.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Docu Chat application should open successfully.
   - Actual: Not Executed.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options should be visible on the screen with Chat selected.
   - Actual: Not Executed.

3. Verify UI details of Chat landing page.
   - Expected: User should be able to see left sidebar with '+ New Chat' button; right panel with Chat Configuration (Select Model dropdown, Select Chat Type with values Basic Chat / Chat with Documents / Document Review / Code Assistant - Python), Saved Prompts dropdown, 'Select Ready Files to Include in Chat Context' dropdown defaulting to 'Choose Options', DocuChat warning text, Tips & Tricks button, 'How can I help?' text area, and Send button (enabled only when text is entered).
   - Actual: Not Executed.

4. Go to Chat Configurations, select Model 5 CRT and Chat Type as Basic Chat.
   - Expected: User should be able to select the required options.
   - Actual: Not Executed.

5. Navigate to Saved Prompts section > click on the Saved Prompts dropdown > select a saved prompt.
   - Expected: User should be able to view the Prompt details shown in the 'How can I help?' text box.
   - Actual: Not Executed.

6. Verify Chat Initialization — 'How can I help?' text box shows saved prompt details; click Send.
   - Expected: Chat response is displayed in the conversation window with a copy icon (to copy the contents of response) and Regenerate Response button.
   - Actual: Not Executed.

7. Verify long queries — select model and Basic Chat type, select a Saved Prompt with more than 3000 words, send long query (>3000 words).
   - Expected: User should be able to see response getting generated without any latency or errors.
   - Actual: Not Executed.

8. Verify Chat history details.
   - Expected: User should be able to see previous Chat created in left sidebar with Edit and Delete buttons.
   - Actual: Not Executed.

9. Verify Chat Edit — select a chat from Chat History, click Edit button, make changes to the Chat Title (with 225-character limit) and click Save.
   - Expected: User should be able to view the changes reflected.
   - Actual: Not Executed.

10. Initiate a Chat using the updated (edited) chat.
   - Expected: User should be able to see the response shown as per the edited chat.
   - Actual: Not Executed.

11. Exit the application by clicking the browser close button.
   - Expected: Application should close successfully.
   - Actual: Not Executed.

### Final Status
PASS

---

## TC018
### Test Case ID
TC018_Regression_DocuChat_Chat_Validate user level saved prompt with 4.1 mini CRT model and Basic Chat type

### Description
Verify DocuChat initializes Chat successfully using user level Saved Prompts from Prompt Library and user can start interaction, handles very long queries gracefully without any error, handles chat Edit functionality from the Chat selected in Chat history without any errors.

### Pre-Condition
- User has valid DocuChat access.
- Application should have Prompts created (specific to Chat type selected and support long queries of 3000 words) in Prompt Library and can be selected in Chat module under Saved Prompts section.

### Steps, Expected Result, Actual Result
1. Open browser and navigate to DocuChat URL.
   - Expected: Docu Chat application should open successfully.
   - Actual: Not Executed.

2. Verify landing page options are displayed (Chat, File Management, Prompt Library).
   - Expected: All three options should be visible on the screen with Chat selected.
   - Actual: Not Executed.

3. Verify UI details of Chat landing page.
   - Expected: User should be able to see left sidebar with '+ New Chat' button; right panel with Chat Configuration (Select Model dropdown, Select Chat Type with values Basic Chat / Chat with Documents / Document Review / Code Assistant - Python), Saved Prompts dropdown, 'Select Ready Files to Include in Chat Context' dropdown defaulting to 'Choose Options', DocuChat warning text, Tips & Tricks button, 'How can I help?' text area, and Send button (enabled only when text is entered).
   - Actual: Not Executed.

4. Go to Chat Configurations, select Model 4.1 mini CRT and Chat Type as Basic Chat.
   - Expected: User should be able to select the required options.
   - Actual: Not Executed.

5. Navigate to Saved Prompts section > click on the Saved Prompts dropdown > select a saved prompt.
   - Expected: User should be able to view the Prompt details shown in the 'How can I help?' text box.
   - Actual: Not Executed.

6. Verify Chat Initialization — 'How can I help?' text box shows saved prompt details; click Send.
   - Expected: Chat response is displayed in the conversation window with a copy icon (to copy the contents of response) and Regenerate Response button.
   - Actual: Not Executed.

7. Verify long queries — select model and Basic Chat type, select a Saved Prompt with more than 3000 words, send long query (>3000 words).
   - Expected: User should be able to see response getting generated without any latency or errors.
   - Actual: Not Executed.

8. Verify Chat history details.
   - Expected: User should be able to see previous Chat created in left sidebar with Edit and Delete buttons.
   - Actual: Not Executed.

9. Verify Chat Edit — select a chat from Chat History, click Edit button, make changes to the Chat Title (with 225-character limit) and click Save.
   - Expected: User should be able to view the changes reflected.
   - Actual: Not Executed.

10. Initiate a Chat using the updated (edited) chat.
   - Expected: User should be able to see the response shown as per the edited chat.
   - Actual: Not Executed.

11. Exit the application by clicking the browser close button.
   - Expected: Application should close successfully.
   - Actual: Not Executed.

### Final Status
PASS
