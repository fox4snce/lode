# ChatVault MVP - API & Backend Testing

**Tester**: AI Assistant  
**Date**: Current Session  
**Scope**: API endpoints, backend functionality, database operations

---

## Test Environment Setup

- [ ] Database initialized
- [ ] Test data available
- [ ] API server accessible
- [ ] All dependencies installed

---

## 1. Database & Setup Tests

### 1.1 Database Initialization
- [ ] Database file created
- [ ] All tables created
- [ ] FTS5 tables created
- [ ] Triggers created

### 1.2 Health Check Endpoint
- [ ] GET /api/health returns 200
- [ ] Response contains expected fields
- [ ] Database status is correct

---

## 2. Import System Tests

### 2.1 Import Endpoints
- [ ] POST /api/import/job creates job
- [ ] Job status endpoint works
- [ ] Import progress tracking works
- [ ] Import reports endpoint works

### 2.2 Import Data Validation
- [ ] OpenAI format validation
- [ ] Claude format validation
- [ ] Error handling for invalid formats

---

## 3. Conversations API Tests

### 3.1 List Conversations
- [ ] GET /api/conversations returns list
- [ ] Sorting works (newest, oldest, longest, most messages)
- [ ] Pagination works
- [ ] Empty state handled

### 3.2 Get Conversation
- [ ] GET /api/conversations/{id} returns conversation
- [ ] Metadata included
- [ ] Error handling for missing conversation

### 3.3 Get Messages
- [ ] GET /api/conversations/{id}/messages returns messages
- [ ] Messages in correct order
- [ ] Pagination works

---

## 4. Search API Tests

### 4.1 Search Endpoint
- [ ] GET /api/search returns results
- [ ] FTS5 search works
- [ ] Query parameter handling
- [ ] Limit/offset pagination
- [ ] Empty results handled

### 4.2 Search Context
- [ ] GET /api/messages/{id}/context returns context
- [ ] Context size is correct
- [ ] Message ordering is correct

---

## 5. Organization API Tests

### 5.1 Tags
- [ ] POST /api/conversations/{id}/tags adds tag
- [ ] DELETE /api/conversations/{id}/tags/{tag} removes tag
- [ ] GET /api/conversations/{id}/tags returns tags

### 5.2 Notes
- [ ] POST /api/conversations/{id}/notes creates note
- [ ] GET /api/conversations/{id}/notes returns notes
- [ ] DELETE /api/conversations/{id}/notes/{note_id} deletes note

### 5.3 Bookmarks
- [ ] POST /api/conversations/{id}/bookmarks creates bookmark
- [ ] GET /api/conversations/{id}/bookmarks returns bookmarks
- [ ] DELETE /api/conversations/{id}/bookmarks/{bookmark_id} deletes bookmark

### 5.4 Stars
- [ ] POST /api/conversations/{id}/star stars conversation
- [ ] DELETE /api/conversations/{id}/star unstars conversation
- [ ] Star status persists

### 5.5 Custom Titles
- [ ] PUT /api/conversations/{id}/title sets custom title
- [ ] Custom title persists
- [ ] Custom title appears in list

---

## 6. Find Tools API Tests

### 6.1 Find Code Blocks
- [ ] GET /api/find/code returns code blocks
- [ ] Results are formatted correctly
- [ ] Context included

### 6.2 Find Links
- [ ] GET /api/find/links returns links
- [ ] Links are extracted correctly
- [ ] Results are formatted correctly

### 6.3 Find TODOs
- [ ] GET /api/find/todos returns TODOs
- [ ] TODOs are detected correctly

### 6.4 Find Questions
- [ ] GET /api/find/questions returns questions
- [ ] Questions are detected correctly

### 6.5 Find Dates
- [ ] GET /api/find/dates returns dates
- [ ] Dates are extracted correctly

### 6.6 Find Decisions
- [ ] GET /api/find/decisions returns decisions
- [ ] Decisions are detected correctly

### 6.7 Find Prompts
- [ ] GET /api/find/prompts returns prompts
- [ ] Prompts are detected correctly

---

## 7. Analytics API Tests

### 7.1 Usage Over Time
- [ ] GET /api/analytics/usage returns usage data
- [ ] Period parameter works (day/week/month)
- [ ] Data is formatted correctly

### 7.2 Longest Streak
- [ ] GET /api/analytics/streaks returns streak data
- [ ] Streak calculation is correct

### 7.3 Top Words
- [ ] GET /api/analytics/words returns top words
- [ ] Word frequency is correct
- [ ] Limit parameter works

### 7.4 Top Phrases
- [ ] GET /api/analytics/phrases returns top phrases
- [ ] Phrase frequency is correct

### 7.5 Vocabulary Trend
- [ ] GET /api/analytics/vocabulary returns vocabulary data
- [ ] Trend calculation is correct

### 7.6 Response Ratio
- [ ] GET /api/analytics/ratios returns ratio data
- [ ] Ratio calculation is correct

### 7.7 Time-of-Day Heatmap
- [ ] GET /api/analytics/heatmap returns heatmap data
- [ ] Data is formatted correctly

---

## 8. Export API Tests

### 8.1 Export Endpoint
- [ ] GET /api/export/{conversation_id} returns export
- [ ] Format parameter works (markdown/json/csv)
- [ ] Options parameter works (timestamps, metadata)
- [ ] Export content is valid

---

## 9. Settings & Management API Tests

### 9.1 Integrity Checks
- [ ] POST /api/settings/integrity runs checks
- [ ] Results are returned
- [ ] Issues are reported

### 9.2 Deduplication
- [ ] POST /api/settings/deduplicate finds duplicates
- [ ] Duplicates are reported correctly

### 9.3 Cleanup
- [ ] POST /api/settings/cleanup wipes imported files
- [ ] Operation completes successfully

---

## 10. Job System Tests

### 10.1 Job Creation
- [ ] Jobs are created with unique IDs
- [ ] Job status is tracked
- [ ] Job progress updates

### 10.2 Job Status
- [ ] GET /api/jobs/{id} returns job status
- [ ] Progress updates are visible
- [ ] Error messages are captured

### 10.3 Job Cancellation
- [ ] POST /api/jobs/{id}/cancel cancels job
- [ ] Job status updates to cancelled

---

## 11. State Management Tests

### 11.1 State Persistence
- [ ] GET /api/state returns current state
- [ ] PUT /api/state saves state
- [ ] State persists across requests

---

## Test Results Summary

**Total Tests**: 75+  
**Passed**: 0 (server not running)  
**Failed**: 0  
**Skipped**: 75+  

**Status**: ⚠️ **Testing requires backend server to be running**

---

## Testing Instructions

### Prerequisites
1. Backend server must be running on `http://localhost:8000`
2. Database must be initialized
3. Test data should be available (imported conversations)

### Running Tests

**Option 1: Automated Testing Script**
```bash
# Start backend server first
python -m backend.main

# In another terminal, run tests
python test_api_endpoints.py
```

**Option 2: Manual API Testing**
Use tools like:
- `curl` commands
- Postman
- HTTPie
- Browser DevTools

---

## Test Coverage

### ✅ Can Be Tested Programmatically
- All GET endpoints (read operations)
- All POST endpoints (create operations)
- All PUT endpoints (update operations)
- All DELETE endpoints (delete operations)
- Response format validation
- Error handling
- Status codes
- Data validation

### ⚠️ Requires Manual Testing
- UI interactions
- Visual rendering
- User experience flows
- Keyboard shortcuts
- Loading states appearance
- Error message display
- Empty states

---

## Issues Found

### Current Issues
1. **Server Not Running**: Tests cannot run without backend server
2. **No Test Data**: Tests require imported conversations to be meaningful

### Recommendations
1. Create a test database with sample data
2. Add automated test setup/teardown
3. Consider using pytest for better test organization
4. Add integration tests that start/stop server automatically

---

## Notes

### Test Script Created
- `test_api_endpoints.py` - Comprehensive API testing script
- Tests all 38+ API endpoints
- Includes error handling and validation
- Provides detailed test results

### Next Steps
1. Start backend server: `python -m backend.main`
2. Import test conversations (use example corpus)
3. Run test script: `python test_api_endpoints.py`
4. Review results and fix any issues found

### Test Data Location
- Example corpus: `data/example_corpus/`
- Contains sample OpenAI and Claude conversation exports

