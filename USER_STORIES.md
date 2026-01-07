# Lode MVP - User Stories for Manual Testing

**Version**: 1.0.0-MVP  
**Purpose**: Comprehensive user stories covering all MVP features for manual testing  
**Format**: Single document with checkboxes for easy tracking

---

## 📋 Table of Contents

1. [First Launch & Setup](#1-first-launch--setup)
2. [Import Conversations](#2-import-conversations)
3. [View Conversations](#3-view-conversations)
4. [Search Conversations](#4-search-conversations)
5. [Organize Conversations](#5-organize-conversations)
6. [Find Tools](#6-find-tools)
7. [Analytics & Insights](#7-analytics--insights)
8. [Export Data](#8-export-data)
9. [Settings & Management](#9-settings--management)
10. [UI/UX & Navigation](#10-uiux--navigation)
11. [Error Handling & Edge Cases](#11-error-handling--edge-cases)

---

## 1. First Launch & Setup

### Story 1.1: First Launch Experience
- [ ] **As a** new user  
- [ ] **I want to** launch Lode for the first time  
- [ ] **So that** I can see a welcome screen and initialize the database

**Test Steps:**
1. Launch the application for the first time
2. Verify welcome/setup screen appears
3. Verify database is initialized automatically
4. Verify I can proceed to the main interface

**Expected Result:** Welcome screen displays, database initializes, user can proceed

---

### Story 1.2: Database Health Check
- [ ] **As a** user  
- [ ] **I want to** verify the database is working  
- [ ] **So that** I know the application is functioning correctly

**Test Steps:**
1. Launch the application
2. Check that no database errors appear
3. Verify the application loads successfully

**Expected Result:** Application starts without database errors

---

## 2. Import Conversations

### Story 2.1: Import OpenAI Conversations
- [ ] **As a** user  
- [ ] **I want to** import my OpenAI conversation exports  
- [ ] **So that** I can view and search my conversations

**Test Steps:**
1. Navigate to Import screen (Menu → Import or Import button)
2. Select "OpenAI" as source type
3. Click file picker and select a valid OpenAI conversation JSON file
4. Enable "Calculate statistics" option
5. Enable "Build search index" option
6. Click "Import"
7. Verify import job is created
8. Verify progress is displayed
9. Wait for import to complete
10. Verify success message appears
11. Verify conversations appear in conversation list

**Expected Result:** OpenAI conversations imported successfully, visible in conversation list

---

### Story 2.2: Import Claude Conversations
- [ ] **As a** user  
- [ ] **I want to** import my Claude conversation exports  
- [ ] **So that** I can view and search my conversations

**Test Steps:**
1. Navigate to Import screen
2. Select "Claude" as source type
3. Click file picker and select a valid Claude conversation JSON file
4. Enable "Calculate statistics" option
5. Enable "Build search index" option
6. Click "Import"
7. Verify import job is created
8. Verify progress is displayed
9. Wait for import to complete
10. Verify success message appears
11. Verify conversations appear in conversation list

**Expected Result:** Claude conversations imported successfully, visible in conversation list

---

### Story 2.3: View Import Progress
- [ ] **As a** user  
- [ ] **I want to** see the progress of my import job  
- [ ] **So that** I know how long it will take

**Test Steps:**
1. Start an import job
2. Click "Jobs" button or open Jobs modal
3. Verify the import job is listed
4. Verify progress percentage is displayed
5. Verify status message is shown
6. Wait for job to complete
7. Verify job status changes to "Completed"

**Expected Result:** Import progress is visible and updates in real-time

---

### Story 2.4: View Import Reports
- [ ] **As a** user  
- [ ] **I want to** view my import history  
- [ ] **So that** I can see what was imported and when

**Test Steps:**
1. Navigate to Import Reports screen (Menu → Import Reports)
2. Verify list of import reports is displayed
3. Click on a report to view details
4. Verify report shows: source file, date, number of conversations imported, status
5. Verify I can see any errors or warnings

**Expected Result:** Import reports are listed with details

---

### Story 2.5: Import Error Handling
- [ ] **As a** user  
- [ ] **I want to** see clear error messages when import fails  
- [ ] **So that** I know what went wrong

**Test Steps:**
1. Navigate to Import screen
2. Select an invalid file (wrong format, corrupted, etc.)
3. Attempt to import
4. Verify error message is displayed
5. Verify error message is user-friendly and actionable

**Expected Result:** Clear error message displayed for invalid imports

---

## 3. View Conversations

### Story 3.1: View Conversation List
- [ ] **As a** user  
- [ ] **I want to** see a list of all my conversations  
- [ ] **So that** I can find and open conversations

**Test Steps:**
1. Launch application (after importing conversations)
2. Verify conversation list appears in left panel
3. Verify conversations are displayed with titles
4. Verify conversations are sorted (default: newest first)
5. Verify I can scroll through the list

**Expected Result:** Conversation list displays all imported conversations

---

### Story 3.2: Select and View Conversation
- [ ] **As a** user  
- [ ] **I want to** click on a conversation to view its messages  
- [ ] **So that** I can read the conversation

**Test Steps:**
1. Click on a conversation in the list
2. Verify conversation is highlighted/selected
3. Verify messages appear in the center panel
4. Verify messages are displayed in chronological order
5. Verify message roles are shown (user/assistant/system)
6. Verify timestamps are displayed

**Expected Result:** Selected conversation displays all messages correctly

---

### Story 3.3: View Conversation Metadata
- [ ] **As a** user  
- [ ] **I want to** see metadata about a conversation  
- [ ] **So that** I can understand its context

**Test Steps:**
1. Select a conversation
2. Verify Inspector panel appears on the right
3. Verify metadata is displayed: conversation ID, date, message count, etc.
4. Verify statistics are shown (if calculated)
5. Verify tags, notes, and bookmarks sections are visible

**Expected Result:** Inspector panel shows all conversation metadata

---

### Story 3.4: Sort Conversations
- [ ] **As a** user  
- [ ] **I want to** sort conversations by different criteria  
- [ ] **So that** I can find conversations more easily

**Test Steps:**
1. Open the sort dropdown in TopBar
2. Select "Newest First"
3. Verify conversations are sorted by date (newest first)
4. Select "Oldest First"
5. Verify conversations are sorted by date (oldest first)
6. Select "Longest First"
7. Verify conversations are sorted by length (longest first)
8. Select "Most Messages"
9. Verify conversations are sorted by message count (most first)

**Expected Result:** Conversations sort correctly for all options

---

### Story 3.5: Restore Last Viewed Conversation
- [ ] **As a** user  
- [ ] **I want to** have the app remember which conversation I was viewing  
- [ ] **So that** I can continue where I left off

**Test Steps:**
1. Select a conversation
2. View some messages
3. Close the application
4. Reopen the application
5. Verify the same conversation is selected and displayed

**Expected Result:** Last viewed conversation is restored on app restart

---

## 4. Search Conversations

### Story 4.1: Basic Search
- [ ] **As a** user  
- [ ] **I want to** search for text across all conversations  
- [ ] **So that** I can find specific information

**Test Steps:**
1. Type a search query in the search box (TopBar)
2. Verify search results appear after debounce delay
3. Verify search results show matching messages
4. Verify search highlights the query term
5. Verify results show conversation context

**Expected Result:** Search returns relevant results with highlighting

---

### Story 4.2: Search with Keyboard Shortcut
- [ ] **As a** user  
- [ ] **I want to** open search with Ctrl+K (Cmd+K on Mac)  
- [ ] **So that** I can search quickly

**Test Steps:**
1. Press Ctrl+K (or Cmd+K on Mac)
2. Verify search input is focused
3. Type a query
4. Verify search executes

**Expected Result:** Keyboard shortcut focuses search input

---

### Story 4.3: Jump to Message from Search
- [ ] **As a** user  
- [ ] **I want to** click on a search result to view the full message  
- [ ] **So that** I can see the context

**Test Steps:**
1. Perform a search
2. Click on a search result
3. Verify the conversation opens
4. Verify the message is displayed
5. Verify the message is highlighted or scrolled into view

**Expected Result:** Clicking search result opens conversation and shows message

---

### Story 4.4: Search Mode Toggle
- [ ] **As a** user  
- [ ] **I want to** toggle between conversation view and search view  
- [ ] **So that** I can easily switch contexts

**Test Steps:**
1. Type a search query
2. Verify view switches to search mode
3. Clear the search query
4. Verify view switches back to conversation mode

**Expected Result:** View mode toggles correctly based on search state

---

### Story 4.5: Empty Search Results
- [ ] **As a** user  
- [ ] **I want to** see a helpful message when search returns no results  
- [ ] **So that** I know the search worked but found nothing

**Test Steps:**
1. Type a search query that matches nothing
2. Verify empty state message is displayed
3. Verify message is helpful (suggests trying different terms)

**Expected Result:** Empty state message displayed for no results

---

## 5. Organize Conversations

### Story 5.1: Add Tags to Conversation
- [ ] **As a** user  
- [ ] **I want to** add tags to conversations  
- [ ] **So that** I can categorize them

**Test Steps:**
1. Select a conversation
2. Open Inspector panel
3. Find "Tags" section
4. Type a tag name in the input field
5. Press Enter or click "Add"
6. Verify tag appears in the tags list
7. Verify tag is saved (refresh or select another conversation and back)

**Expected Result:** Tags can be added and persist

---

### Story 5.2: Remove Tags from Conversation
- [ ] **As a** user  
- [ ] **I want to** remove tags from conversations  
- [ ] **So that** I can update categorization

**Test Steps:**
1. Select a conversation with existing tags
2. Open Inspector panel
3. Find "Tags" section
4. Click remove/delete button on a tag
5. Verify tag is removed from the list
6. Verify tag removal is saved

**Expected Result:** Tags can be removed and changes persist

---

### Story 5.3: Create Note on Conversation
- [ ] **As a** user  
- [ ] **I want to** create notes on conversations  
- [ ] **So that** I can add my own comments

**Test Steps:**
1. Select a conversation
2. Open Inspector panel
3. Find "Notes" section
4. Click "Add Note" or similar button
5. Enter note text
6. Save the note
7. Verify note appears in the notes list
8. Verify note is saved

**Expected Result:** Notes can be created and persist

---

### Story 5.4: View Notes on Conversation
- [ ] **As a** user  
- [ ] **I want to** view notes I've created on conversations  
- [ ] **So that** I can see my comments

**Test Steps:**
1. Select a conversation with existing notes
2. Open Inspector panel
3. Find "Notes" section
4. Verify all notes are displayed
5. Verify note text is readable

**Expected Result:** All notes are displayed in Inspector panel

---

### Story 5.5: Create Bookmark on Message
- [ ] **As a** user  
- [ ] **I want to** bookmark specific messages  
- [ ] **So that** I can quickly return to them

**Test Steps:**
1. Select a conversation
2. View messages in the center panel
3. Find a message to bookmark
4. Open Inspector panel
5. Find "Bookmarks" section
6. Click "Add Bookmark" or similar
7. Enter bookmark name/description
8. Save the bookmark
9. Verify bookmark appears in the bookmarks list
10. Verify bookmark links to the correct message

**Expected Result:** Bookmarks can be created and link to messages

---

### Story 5.6: View Bookmarks
- [ ] **As a** user  
- [ ] **I want to** view bookmarks I've created  
- [ ] **So that** I can navigate to important messages

**Test Steps:**
1. Select a conversation with bookmarks
2. Open Inspector panel
3. Find "Bookmarks" section
4. Verify all bookmarks are listed
5. Click on a bookmark
6. Verify the message is displayed and scrolled into view

**Expected Result:** Bookmarks are listed and can be clicked to jump to messages

---

### Story 5.7: Star Conversation
- [ ] **As a** user  
- [ ] **I want to** star conversations  
- [ ] **So that** I can mark important ones

**Test Steps:**
1. Select a conversation
2. Open Inspector panel
3. Find "Star" or favorite option
4. Click to star the conversation
5. Verify star icon appears/updates
6. Verify star status is saved

**Expected Result:** Conversations can be starred and status persists

---

### Story 5.8: Unstar Conversation
- [ ] **As a** user  
- [ ] **I want to** unstar conversations  
- [ ] **So that** I can update my favorites

**Test Steps:**
1. Select a starred conversation
2. Open Inspector panel
3. Find "Star" option
4. Click to unstar the conversation
5. Verify star icon updates
6. Verify unstar status is saved

**Expected Result:** Conversations can be unstarred and status persists

---

### Story 5.9: Set Custom Title
- [ ] **As a** user  
- [ ] **I want to** set a custom title for a conversation  
- [ ] **So that** I can identify it more easily

**Test Steps:**
1. Select a conversation
2. Open Inspector panel
3. Find "Custom Title" or "Title" section
4. Enter a custom title
5. Save the title
6. Verify custom title appears in conversation list
7. Verify custom title is saved

**Expected Result:** Custom titles can be set and appear in conversation list

---

## 6. Find Tools

### Story 6.1: Access Find Tools Screen
- [ ] **As a** user  
- [ ] **I want to** access the Find Tools screen  
- [ ] **So that** I can use specialized search tools

**Test Steps:**
1. Navigate to Find Tools screen (Menu → Find Tools)
2. Verify screen loads
3. Verify all tool buttons are visible

**Expected Result:** Find Tools screen displays with all tools

---

### Story 6.2: Find Code Blocks
- [ ] **As a** user  
- [ ] **I want to** find all code blocks in my conversations  
- [ ] **So that** I can locate code snippets

**Test Steps:**
1. Navigate to Find Tools screen
2. Click "Find Code Blocks" button
3. Verify results are displayed
4. Verify results show code blocks with context
5. Verify I can click results to view full messages

**Expected Result:** Code blocks are found and displayed

---

### Story 6.3: Find Links
- [ ] **As a** user  
- [ ] **I want to** find all links in my conversations  
- [ ] **So that** I can locate URLs

**Test Steps:**
1. Navigate to Find Tools screen
2. Click "Find Links" button
3. Verify results are displayed
4. Verify results show links with context
5. Verify I can click results to view full messages

**Expected Result:** Links are found and displayed

---

### Story 6.4: Find TODOs
- [ ] **As a** user  
- [ ] **I want to** find all TODOs in my conversations  
- [ ] **So that** I can track tasks

**Test Steps:**
1. Navigate to Find Tools screen
2. Click "Find TODOs" button
3. Verify results are displayed
4. Verify results show TODO items with context
5. Verify I can click results to view full messages

**Expected Result:** TODOs are found and displayed

---

### Story 6.5: Find Questions
- [ ] **As a** user  
- [ ] **I want to** find all questions in my conversations  
- [ ] **So that** I can review what I asked

**Test Steps:**
1. Navigate to Find Tools screen
2. Click "Find Questions" button
3. Verify results are displayed
4. Verify results show questions with context
5. Verify I can click results to view full messages

**Expected Result:** Questions are found and displayed

---

### Story 6.6: Find Dates
- [ ] **As a** user  
- [ ] **I want to** find all dates mentioned in my conversations  
- [ ] **So that** I can find time-sensitive information

**Test Steps:**
1. Navigate to Find Tools screen
2. Click "Find Dates" button
3. Verify results are displayed
4. Verify results show dates with context
5. Verify I can click results to view full messages

**Expected Result:** Dates are found and displayed

---

### Story 6.7: Find Decisions
- [ ] **As a** user  
- [ ] **I want to** find all decisions mentioned in my conversations  
- [ ] **So that** I can review important choices

**Test Steps:**
1. Navigate to Find Tools screen
2. Click "Find Decisions" button
3. Verify results are displayed
4. Verify results show decisions with context
5. Verify I can click results to view full messages

**Expected Result:** Decisions are found and displayed

---

### Story 6.8: Find Prompts
- [ ] **As a** user  
- [ ] **I want to** find all prompts in my conversations  
- [ ] **So that** I can review my prompts

**Test Steps:**
1. Navigate to Find Tools screen
2. Click "Find Prompts" button
3. Verify results are displayed
4. Verify results show prompts with context
5. Verify I can click results to view full messages

**Expected Result:** Prompts are found and displayed

---

## 7. Analytics & Insights

### Story 7.1: Access Analytics Screen
- [ ] **As a** user  
- [ ] **I want to** view analytics about my conversations  
- [ ] **So that** I can understand my usage patterns

**Test Steps:**
1. Navigate to Analytics screen (Menu → Analytics)
2. Verify screen loads
3. Verify tabs are visible for different analytics views

**Expected Result:** Analytics screen displays with tabs

---

### Story 7.2: View Usage Over Time
- [ ] **As a** user  
- [ ] **I want to** see my conversation usage over time  
- [ ] **So that** I can track my activity

**Test Steps:**
1. Navigate to Analytics screen
2. Click "Usage" tab
3. Verify usage data is displayed
4. Change period to "Day" and verify data updates
5. Change period to "Week" and verify data updates
6. Change period to "Month" and verify data updates

**Expected Result:** Usage over time is displayed and updates with period selection

---

### Story 7.3: View Longest Streak
- [ ] **As a** user  
- [ ] **I want to** see my longest conversation streak  
- [ ] **So that** I can see my consistency

**Test Steps:**
1. Navigate to Analytics screen
2. Click "Streaks" tab
3. Verify longest streak is displayed
4. Verify streak information is accurate

**Expected Result:** Longest streak is displayed correctly

---

### Story 7.4: View Top Words
- [ ] **As a** user  
- [ ] **I want to** see my most used words  
- [ ] **So that** I can understand my vocabulary

**Test Steps:**
1. Navigate to Analytics screen
2. Click "Words" tab
3. Verify top words are displayed in a table
4. Verify words are sorted by frequency
5. Verify word counts are shown

**Expected Result:** Top words are displayed in a table

---

### Story 7.5: View Top Phrases
- [ ] **As a** user  
- [ ] **I want to** see my most used phrases  
- [ ] **So that** I can understand my communication patterns

**Test Steps:**
1. Navigate to Analytics screen
2. Click "Phrases" tab
3. Verify top phrases are displayed in a table
4. Verify phrases are sorted by frequency
5. Verify phrase counts are shown

**Expected Result:** Top phrases are displayed in a table

---

### Story 7.6: View Vocabulary Trend
- [ ] **As a** user  
- [ ] **I want to** see how my vocabulary changes over time  
- [ ] **So that** I can track my language development

**Test Steps:**
1. Navigate to Analytics screen
2. Click "Vocabulary" tab
3. Verify vocabulary trend is displayed
4. Verify data shows vocabulary over time

**Expected Result:** Vocabulary trend is displayed

---

### Story 7.7: View Response Ratio
- [ ] **As a** user  
- [ ] **I want to** see the ratio of my messages to assistant messages  
- [ ] **So that** I can understand conversation balance

**Test Steps:**
1. Navigate to Analytics screen
2. Click "Ratios" tab
3. Verify response ratio is displayed
4. Verify ratio is calculated correctly

**Expected Result:** Response ratio is displayed correctly

---

### Story 7.8: View Time-of-Day Heatmap
- [ ] **As a** user  
- [ ] **I want to** see when I have conversations throughout the day  
- [ ] **So that** I can understand my usage patterns

**Test Steps:**
1. Navigate to Analytics screen
2. Click "Heatmap" tab
3. Verify time-of-day heatmap is displayed
4. Verify data shows activity by hour/day

**Expected Result:** Time-of-day heatmap is displayed

---

## 8. Export Data

### Story 8.1: Access Export Screen
- [ ] **As a** user  
- [ ] **I want to** export my conversations  
- [ ] **So that** I can backup or share them

**Test Steps:**
1. Navigate to Export screen (Menu → Export)
2. Verify screen loads
3. Verify conversation selector is visible
4. Verify format options are visible

**Expected Result:** Export screen displays with all options

---

### Story 8.2: Export Conversation as Markdown
- [ ] **As a** user  
- [ ] **I want to** export a conversation as Markdown  
- [ ] **So that** I can use it in documentation

**Test Steps:**
1. Navigate to Export screen
2. Select a conversation from the dropdown
3. Select "Markdown" format
4. Enable/disable options (timestamps, metadata)
5. Click "Export"
6. Verify export content is displayed
7. Verify Markdown format is correct

**Expected Result:** Conversation is exported as Markdown

---

### Story 8.3: Export Conversation as JSON
- [ ] **As a** user  
- [ ] **I want to** export a conversation as JSON  
- [ ] **So that** I can use it programmatically

**Test Steps:**
1. Navigate to Export screen
2. Select a conversation from the dropdown
3. Select "JSON" format
4. Enable/disable options (timestamps, metadata)
5. Click "Export"
6. Verify export content is displayed
7. Verify JSON format is valid

**Expected Result:** Conversation is exported as valid JSON

---

### Story 8.4: Export Conversation as CSV
- [ ] **As a** user  
- [ ] **I want to** export a conversation as CSV  
- [ ] **So that** I can analyze it in spreadsheets

**Test Steps:**
1. Navigate to Export screen
2. Select a conversation from the dropdown
3. Select "CSV" format
4. Enable/disable options (timestamps, metadata)
5. Click "Export"
6. Verify export content is displayed
7. Verify CSV format is correct

**Expected Result:** Conversation is exported as CSV

---

### Story 8.5: Export with Options
- [ ] **As a** user  
- [ ] **I want to** control what is included in exports  
- [ ] **So that** I can customize the output

**Test Steps:**
1. Navigate to Export screen
2. Select a conversation
3. Select a format
4. Toggle "Include timestamps" on/off
5. Toggle "Include metadata" on/off
6. Export and verify options are respected

**Expected Result:** Export options control what is included

---

## 9. Settings & Management

### Story 9.1: Access Settings Screen
- [ ] **As a** user  
- [ ] **I want to** access settings and management tools  
- [ ] **So that** I can maintain my database

**Test Steps:**
1. Navigate to Settings screen (Menu → Settings)
2. Verify screen loads
3. Verify tabs are visible: Integrity, Deduplication, Cleanup, Encryption

**Expected Result:** Settings screen displays with tabs

---

### Story 9.2: Run Integrity Checks
- [ ] **As a** user  
- [ ] **I want to** check database integrity  
- [ ] **So that** I can ensure data is valid

**Test Steps:**
1. Navigate to Settings screen
2. Click "Integrity" tab
3. Click "Run Integrity Checks" button
4. Verify checks run
5. Verify results are displayed
6. Verify any issues are reported

**Expected Result:** Integrity checks run and display results

---

### Story 9.3: Find Duplicates
- [ ] **As a** user  
- [ ] **I want to** find duplicate conversations  
- [ ] **So that** I can clean up my database

**Test Steps:**
1. Navigate to Settings screen
2. Click "Deduplication" tab
3. Click "Find Duplicates" button
4. Verify duplicate detection runs
5. Verify duplicates are listed
6. Verify duplicate details are shown

**Expected Result:** Duplicates are found and displayed

---

### Story 9.4: Wipe Imported Files
- [ ] **As a** user  
- [ ] **I want to** remove imported file references  
- [ ] **So that** I can clean up metadata

**Test Steps:**
1. Navigate to Settings screen
2. Click "Cleanup" tab
3. Click "Wipe Imported Files" button
4. Verify confirmation dialog appears (if implemented)
5. Confirm the action
6. Verify operation completes
7. Verify imported file references are removed

**Expected Result:** Imported file references are removed

---

### Story 9.5: View Encryption Tab
- [ ] **As a** user  
- [ ] **I want to** see encryption options (placeholder)  
- [ ] **So that** I know it's planned

**Test Steps:**
1. Navigate to Settings screen
2. Click "Encryption" tab
3. Verify placeholder content is displayed
4. Verify it indicates encryption is not yet implemented

**Expected Result:** Encryption tab displays placeholder

---

## 10. UI/UX & Navigation

### Story 10.1: Navigate with Menu Bar
- [ ] **As a** user  
- [ ] **I want to** navigate between screens using the menu  
- [ ] **So that** I can access all features

**Test Steps:**
1. Verify MenuBar is visible at the top
2. Click each menu item:
   - Import
   - Analytics
   - Find Tools
   - Export
   - Import Reports
   - Settings
   - Help → About
3. Verify each screen loads correctly
4. Verify I can navigate back to main view

**Expected Result:** All menu items navigate to correct screens

---

### Story 10.2: Use Keyboard Shortcuts
- [ ] **As a** user  
- [ ] **I want to** use keyboard shortcuts  
- [ ] **So that** I can work faster

**Test Steps:**
1. Press Ctrl+K (Cmd+K on Mac) - verify search focuses
2. Press Escape - verify modals/dialogs close
3. Use Arrow keys in conversation list - verify navigation works
4. Verify shortcuts work as expected

**Expected Result:** Keyboard shortcuts work correctly

---

### Story 10.3: See Loading States
- [ ] **As a** user  
- [ ] **I want to** see loading indicators  
- [ ] **So that** I know the app is working

**Test Steps:**
1. Perform actions that take time (import, search, analytics)
2. Verify loading spinners appear
3. Verify spinners disappear when operation completes

**Expected Result:** Loading states are displayed during async operations

---

### Story 10.4: See Error Messages
- [ ] **As a** user  
- [ ] **I want to** see clear error messages  
- [ ] **So that** I know what went wrong

**Test Steps:**
1. Trigger error scenarios (invalid file, network error, etc.)
2. Verify error messages are displayed
3. Verify error messages are user-friendly
4. Verify error messages are actionable

**Expected Result:** Error messages are clear and helpful

---

### Story 10.5: See Empty States
- [ ] **As a** user  
- [ ] **I want to** see helpful messages when there's no data  
- [ ] **So that** I know what to do

**Test Steps:**
1. View empty conversation list (before first import)
2. Verify empty state message is displayed
3. Verify message suggests importing conversations
4. Perform empty search
5. Verify empty state message is displayed

**Expected Result:** Empty states are helpful and actionable

---

### Story 10.6: View About Screen
- [ ] **As a** user  
- [ ] **I want to** see information about the application  
- [ ] **So that** I can learn more and support development

**Test Steps:**
1. Navigate to About screen (Menu → Help → About)
2. Verify application information is displayed
3. Verify version number is shown
4. Verify Ko-fi link is present and clickable
5. Verify link goes to recursiverealms Ko-fi page

**Expected Result:** About screen displays app info and Ko-fi link

---

## 11. Error Handling & Edge Cases

### Story 11.1: Handle Empty Database
- [ ] **As a** user  
- [ ] **I want to** use the app with no conversations  
- [ ] **So that** I can start fresh

**Test Steps:**
1. Launch app with empty database
2. Verify welcome/empty states are displayed
3. Verify I can still navigate to Import screen
4. Verify no errors occur

**Expected Result:** App handles empty database gracefully

---

### Story 11.2: Handle Large Imports
- [ ] **As a** user  
- [ ] **I want to** import large conversation files  
- [ ] **So that** I can import all my data

**Test Steps:**
1. Import a large conversation file (100+ conversations)
2. Verify import progresses correctly
3. Verify progress updates are shown
4. Verify import completes successfully
5. Verify all conversations are imported

**Expected Result:** Large imports work correctly

---

### Story 11.3: Handle Invalid File Formats
- [ ] **As a** user  
- [ ] **I want to** see clear errors for invalid files  
- [ ] **So that** I know what to fix

**Test Steps:**
1. Attempt to import a non-JSON file
2. Attempt to import a JSON file with wrong structure
3. Verify error messages are clear
4. Verify error messages suggest correct format

**Expected Result:** Invalid files show helpful error messages

---

### Story 11.4: Handle Network Errors (if applicable)
- [ ] **As a** user  
- [ ] **I want to** see errors when network requests fail  
- [ ] **So that** I know what happened

**Test Steps:**
1. Simulate network error (if applicable)
2. Verify error message is displayed
3. Verify retry option is available (if implemented)

**Expected Result:** Network errors are handled gracefully

---

### Story 11.5: Handle Concurrent Operations
- [ ] **As a** user  
- [ ] **I want to** perform multiple operations  
- [ ] **So that** I can work efficiently

**Test Steps:**
1. Start an import job
2. While import is running, navigate to other screens
3. Perform searches
4. View conversations
5. Verify all operations work correctly
6. Verify no conflicts occur

**Expected Result:** Multiple operations work concurrently

---

## 📊 Testing Progress Summary

**Total Stories**: 75  
**Completed**: ___ / 75  
**In Progress**: ___ / 75  
**Not Started**: ___ / 75

---

## 📝 Notes

- Check off each story as you complete testing
- Note any bugs or issues found
- Verify expected results match actual behavior
- Test both happy paths and edge cases

---

**Last Updated**: [Date]  
**Tester**: [Name]  
**Version Tested**: 1.0.0-MVP

