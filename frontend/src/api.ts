/**
 * API client for Lode backend.
 */

const API_BASE = '/api'

export interface Conversation {
  conversation_id: string
  title: string | null
  create_time: number | null
  update_time: number | null
  message_count: number
  word_count: number
  ai_source: string | null
  is_starred: boolean
  tags: string[]
}

export interface Message {
  message_id: string
  role: string
  content: string
  create_time: number | null
  parent_id: string | null
}

export interface SearchHit {
  conversation_id: string
  message_id: string
  content: string
  role: string
  create_time: number | null
}

export interface Job {
  id: string
  job_type: string
  status: string
  progress: number
  message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  result: any
  error: string | null
}

export interface State {
  last_conversation_id: string | null
  last_message_id: string | null
  last_scroll_offset: number | null
}

// Core
export async function checkSetup(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/setup/check`)
    if (!res.ok) {
      console.error('Setup check failed:', res.status, res.statusText)
      return false
    }
    const data = await res.json()
    return data.initialized ?? false
  } catch (error) {
    console.error('Setup check error:', error)
    return false
  }
}

export async function initializeDatabase(): Promise<void> {
  const res = await fetch(`${API_BASE}/setup/initialize`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to initialize database')
}

// Conversations
export async function listConversations(params: {
  sort?: string
  q?: string
  tag?: string
  date_from?: string
  date_to?: string
  starred?: boolean
  limit?: number
  offset?: number
}): Promise<Conversation[]> {
  const query = new URLSearchParams()
  if (params.sort) query.append('sort', params.sort)
  if (params.q) query.append('q', params.q)
  if (params.tag) query.append('tag', params.tag)
  if (params.date_from) query.append('date_from', params.date_from)
  if (params.date_to) query.append('date_to', params.date_to)
  if (params.starred !== undefined) query.append('starred', String(params.starred))
  if (params.limit) query.append('limit', String(params.limit))
  if (params.offset) query.append('offset', String(params.offset))
  
  const res = await fetch(`${API_BASE}/conversations?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load conversations' }))
    throw new Error(error.detail || 'Failed to load conversations')
  }
  return res.json()
}

export async function getConversation(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/conversations/${id}`)
  if (!res.ok) throw new Error('Conversation not found')
  return res.json()
}

export async function getMessages(
  conversationId: string,
  params?: {
    anchor_message_id?: string
    direction?: 'older' | 'newer' | 'around'
    limit?: number
  }
): Promise<Message[]> {
  const query = new URLSearchParams()
  if (params?.anchor_message_id) query.append('anchor_message_id', params.anchor_message_id)
  if (params?.direction) query.append('direction', params.direction)
  if (params?.limit) query.append('limit', String(params.limit))
  
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load messages' }))
    throw new Error(error.detail || 'Failed to load messages')
  }
  return res.json()
}

export async function getMessageContext(messageId: string, n: number = 5): Promise<Message[]> {
  const res = await fetch(`${API_BASE}/messages/${messageId}/context?n=${n}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load message context' }))
    throw new Error(error.detail || 'Failed to load message context')
  }
  return res.json()
}

// Organization (Tags, Notes, Bookmarks)
export async function getTags(conversationId: string): Promise<string[]> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/tags`)
  if (!res.ok) {
    // Tags might not exist, return empty array
    return []
  }
  return res.json()
}

export async function addTag(conversationId: string, tagName: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: tagName })
  })
  if (!res.ok) throw new Error('Failed to add tag')
}

export async function removeTag(conversationId: string, tagName: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/tags/${encodeURIComponent(tagName)}`, {
    method: 'DELETE'
  })
  if (!res.ok) throw new Error('Failed to remove tag')
}

export async function getNotes(conversationId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/notes`)
  if (!res.ok) {
    // Notes might not exist, return empty array
    return []
  }
  return res.json()
}

export async function createNote(conversationId: string, noteText: string, messageId?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note_text: noteText, message_id: messageId })
  })
  if (!res.ok) throw new Error('Failed to create note')
}

export async function getBookmarks(conversationId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/bookmarks`)
  if (!res.ok) {
    // Bookmarks might not exist, return empty array
    return []
  }
  return res.json()
}

export async function createBookmark(conversationId: string, messageId?: string, note?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/bookmarks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message_id: messageId, note })
  })
  if (!res.ok) throw new Error('Failed to create bookmark')
}

// Search
export async function search(params: {
  q: string
  conversation_id?: string
  limit?: number
  offset?: number
}): Promise<SearchHit[]> {
  const query = new URLSearchParams()
  query.append('q', params.q)
  if (params.conversation_id) query.append('conversation_id', params.conversation_id)
  if (params.limit) query.append('limit', String(params.limit))
  if (params.offset) query.append('offset', String(params.offset))
  
  const res = await fetch(`${API_BASE}/search?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Search failed' }))
    throw new Error(error.detail || 'Search failed')
  }
  return res.json()
}

// Jobs
export async function createImportJob(params: {
  source_type: string
  file_path: string
  calculate_stats?: boolean
  build_index?: boolean
}): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/jobs/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to create import job' }))
    throw new Error(error.detail || 'Failed to create import job')
  }
  return res.json()
}

export async function createReindexJob(): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/jobs/reindex`, { method: 'POST' })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to create reindex job' }))
    throw new Error(error.detail || 'Failed to create reindex job')
  }
  return res.json()
}

export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/jobs`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load jobs' }))
    throw new Error(error.detail || 'Failed to load jobs')
  }
  return res.json()
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load job' }))
    throw new Error(error.detail || 'Failed to load job')
  }
  return res.json()
}

export async function cancelJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, { method: 'POST' })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to cancel job' }))
    throw new Error(error.detail || 'Failed to cancel job')
  }
}

// State
export async function getState(): Promise<State> {
  const res = await fetch(`${API_BASE}/state`)
  if (!res.ok) {
    // State endpoint might not exist, return default state
    return { last_conversation_id: null, last_message_id: null, last_scroll_offset: null }
  }
  return res.json()
}

export async function saveState(state: State): Promise<void> {
  const res = await fetch(`${API_BASE}/state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state)
  })
  if (!res.ok) {
    // Silently fail for state saving - not critical
    console.warn('Failed to save state')
  }
}

// Analytics
export async function getUsageOverTime(params: {
  period?: 'day' | 'week' | 'month'
  start_date?: string
  end_date?: string
}): Promise<any[]> {
  const query = new URLSearchParams()
  if (params.period) query.append('period', params.period)
  if (params.start_date) query.append('start_date', params.start_date)
  if (params.end_date) query.append('end_date', params.end_date)
  const res = await fetch(`${API_BASE}/analytics/usage?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load usage data' }))
    throw new Error(error.detail || 'Failed to load usage data')
  }
  return res.json()
}

export async function getLongestStreak(): Promise<any> {
  const res = await fetch(`${API_BASE}/analytics/streaks`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load streak data' }))
    throw new Error(error.detail || 'Failed to load streak data')
  }
  return res.json()
}

export async function getTopWords(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/analytics/top-words?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load top words' }))
    throw new Error(error.detail || 'Failed to load top words')
  }
  return res.json()
}

export async function getTopPhrases(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/analytics/top-phrases?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load top phrases' }))
    throw new Error(error.detail || 'Failed to load top phrases')
  }
  return res.json()
}

export async function getVocabularyTrend(period?: 'day' | 'week' | 'month'): Promise<any[]> {
  const query = new URLSearchParams()
  if (period) query.append('period', period)
  const res = await fetch(`${API_BASE}/analytics/vocabulary?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load vocabulary trend' }))
    throw new Error(error.detail || 'Failed to load vocabulary trend')
  }
  return res.json()
}

export async function getResponseRatio(): Promise<any> {
  const res = await fetch(`${API_BASE}/analytics/response-ratio`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load response ratio' }))
    throw new Error(error.detail || 'Failed to load response ratio')
  }
  return res.json()
}

export async function getTimeOfDayHeatmap(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/analytics/heatmap`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load heatmap data' }))
    throw new Error(error.detail || 'Failed to load heatmap data')
  }
  return res.json()
}

// Find Tools
export async function findCodeBlocks(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/find/code?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to find code blocks' }))
    throw new Error(error.detail || 'Failed to find code blocks')
  }
  return res.json()
}

export async function findLinks(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/find/links?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to find links' }))
    throw new Error(error.detail || 'Failed to find links')
  }
  return res.json()
}

export async function findTodos(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/find/todos?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to find TODOs' }))
    throw new Error(error.detail || 'Failed to find TODOs')
  }
  return res.json()
}

export async function findQuestions(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/find/questions?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to find questions' }))
    throw new Error(error.detail || 'Failed to find questions')
  }
  return res.json()
}

export async function findDates(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/find/dates?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to find dates' }))
    throw new Error(error.detail || 'Failed to find dates')
  }
  return res.json()
}

export async function findDecisions(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/find/decisions?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to find decisions' }))
    throw new Error(error.detail || 'Failed to find decisions')
  }
  return res.json()
}

export async function findPrompts(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/find/prompts?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to find prompts' }))
    throw new Error(error.detail || 'Failed to find prompts')
  }
  return res.json()
}

// Import Reports
export async function listImportReports(limit?: number): Promise<any[]> {
  const query = new URLSearchParams()
  if (limit) query.append('limit', String(limit))
  const res = await fetch(`${API_BASE}/import/reports?${query}`)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to load import reports' }))
    throw new Error(error.detail || 'Failed to load import reports')
  }
  return res.json()
}

export async function getImportReport(batchId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/import/reports/${batchId}`)
  if (!res.ok) throw new Error('Import report not found')
  return res.json()
}

// Export
export async function exportConversation(
  conversationId: string,
  format: 'markdown' | 'csv' | 'json' = 'markdown',
  includeTimestamps: boolean = true,
  includeMetadata: boolean = true
): Promise<any> {
  const query = new URLSearchParams()
  query.append('format', format)
  query.append('include_timestamps', String(includeTimestamps))
  query.append('include_metadata', String(includeMetadata))
  const res = await fetch(`${API_BASE}/export/conversation/${conversationId}?${query}`, {
    method: 'POST'
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to export conversation' }))
    throw new Error(error.detail || 'Failed to export conversation')
  }
  return res.json()
}

// Integrity Checks
export async function runIntegrityChecks(): Promise<any> {
  const res = await fetch(`${API_BASE}/integrity/check`)
  return res.json()
}

// Deduplication
export async function findDuplicateMessages(conversationId?: string): Promise<any[]> {
  const query = new URLSearchParams()
  if (conversationId) query.append('conversation_id', conversationId)
  const res = await fetch(`${API_BASE}/deduplication/find-messages?${query}`)
  return res.json()
}

export async function findDuplicateConversations(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/deduplication/find-conversations`)
  return res.json()
}

export async function getDeduplicationStats(): Promise<any> {
  const res = await fetch(`${API_BASE}/deduplication/stats`)
  return res.json()
}

// Cleanup
export async function listImportedFiles(batchId?: string): Promise<any[]> {
  const query = new URLSearchParams()
  if (batchId) query.append('import_batch_id', batchId)
  const res = await fetch(`${API_BASE}/cleanup/files?${query}`)
  return res.json()
}

export async function wipeImportedFiles(batchId?: string, verify: boolean = true, dryRun: boolean = false): Promise<any> {
  const body: any = { verify, dry_run: dryRun }
  if (batchId) body.import_batch_id = batchId
  const res = await fetch(`${API_BASE}/cleanup/wipe-files`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  return res.json()
}

