import React, { useState, useEffect } from 'react'
import ConversationList from '../components/ConversationList'
import MessageViewer from '../components/MessageViewer'
import Inspector from '../components/Inspector'
import TopBar from '../components/TopBar'
import MenuBar from '../components/MenuBar'
import JobsModal from '../components/JobsModal'
import SearchResults from '../components/SearchResults'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { listConversations, getState, saveState, search, SearchHit } from '../api'

interface Props {
  onImport: () => void
  onAnalytics?: () => void
  onFindTools?: () => void
  onExport?: () => void
  onSettings?: () => void
  onImportReports?: () => void
  onAbout?: () => void
}

type ViewMode = 'conversations' | 'search'

export default function MainShell({ 
  onImport, 
  onAnalytics, 
  onFindTools, 
  onExport, 
  onSettings, 
  onImportReports,
  onAbout
}: Props) {
  const [conversations, setConversations] = useState<any[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [highlightMessageId, setHighlightMessageId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('conversations')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchHit[]>([])
  const [sort, setSort] = useState('newest')
  const [showJobs, setShowJobs] = useState(false)
  const [loading, setLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)

  useEffect(() => {
    if (viewMode === 'conversations') {
      loadConversations()
    }
    restoreState()
  }, [sort, viewMode])

  // Debounced search - trigger when typing in search box
  useEffect(() => {
    if (searchQuery.trim()) {
      const timeoutId = setTimeout(() => {
        performSearch()
      }, 500)
      return () => clearTimeout(timeoutId)
    } else {
      // Clear search results when query is empty
      setSearchResults([])
      if (viewMode === 'search') {
        setViewMode('conversations')
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery])

  const loadConversations = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listConversations({ sort, limit: 50 })
      setConversations(data || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load conversations')
      setConversations([])
    } finally {
      setLoading(false)
    }
  }

  const restoreState = async () => {
    try {
      const state = await getState()
      if (state.last_conversation_id) {
        setSelectedId(state.last_conversation_id)
      }
    } catch {
      // Fallback to localStorage
      const saved = localStorage.getItem('last_conversation_id')
      if (saved) setSelectedId(saved)
    }
  }

  const performSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      setSearchError(null)
      return
    }

    setSearchLoading(true)
    setSearchError(null)
    try {
      const results = await search({ q: searchQuery.trim(), limit: 50 })
      setSearchResults(results || [])
      // Force switch to search view
      setViewMode('search')
    } catch (err: any) {
      const errorMsg = err.message || 'Search failed. Please try again.'
      setSearchError(errorMsg)
      setSearchResults([])
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSelectConversation = async (id: string) => {
    setSelectedId(id)
    setViewMode('conversations')
    // Save state
    try {
      await saveState({ last_conversation_id: id, last_message_id: null, last_scroll_offset: null })
    } catch {
      localStorage.setItem('last_conversation_id', id)
    }
  }

  const handleSelectSearchHit = async (hit: SearchHit) => {
    setSelectedId(hit.conversation_id)
    setHighlightMessageId(hit.message_id)
    setViewMode('conversations')
    // Clear highlight after a few seconds
    setTimeout(() => setHighlightMessageId(null), 5000)
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't handle shortcuts when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        // Allow Ctrl+K even in inputs
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
          e.preventDefault()
          const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement
          searchInput?.focus()
          searchInput?.select()
        }
        return
      }

      // Ctrl+K or Cmd+K: Focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement
        searchInput?.focus()
        searchInput?.select()
      }
      // Escape: Close modals
      if (e.key === 'Escape') {
        if (showJobs) {
          setShowJobs(false)
        }
      }
      // Arrow keys: Navigate conversations
      if (e.key === 'ArrowDown' && viewMode === 'conversations' && conversations.length > 0) {
        e.preventDefault()
        const currentIndex = conversations.findIndex(c => c.conversation_id === selectedId)
        const nextIndex = currentIndex < conversations.length - 1 ? currentIndex + 1 : 0
        handleSelectConversation(conversations[nextIndex].conversation_id)
      }
      if (e.key === 'ArrowUp' && viewMode === 'conversations' && conversations.length > 0) {
        e.preventDefault()
        const currentIndex = conversations.findIndex(c => c.conversation_id === selectedId)
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : conversations.length - 1
        handleSelectConversation(conversations[prevIndex].conversation_id)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [showJobs, viewMode, conversations, selectedId])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <MenuBar
        onImport={onImport}
        onExport={onExport || (() => {})}
        onAnalytics={onAnalytics || (() => {})}
        onFindTools={onFindTools || (() => {})}
        onImportReports={onImportReports || (() => {})}
        onSettings={onSettings || (() => {})}
        onAbout={onAbout || (() => {})}
      />
      <TopBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sort={sort}
        onSortChange={setSort}
        onJobsClick={() => setShowJobs(true)}
        onImport={onImport}
      />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '300px', borderRight: '1px solid #e0e0e0', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '8px', borderBottom: '1px solid #e0e0e0', display: 'flex', gap: '8px' }}>
            <button
              onClick={() => {
                setViewMode('conversations')
                setSearchQuery('')
              }}
              style={{
                flex: 1,
                padding: '6px',
                border: 'none',
                background: viewMode === 'conversations' ? '#e3f2fd' : 'transparent',
                cursor: 'pointer'
              }}
            >
              Conversations
            </button>
            <button
              onClick={() => {
                setViewMode('search')
                if (searchQuery) performSearch()
              }}
              style={{
                flex: 1,
                padding: '6px',
                border: 'none',
                background: viewMode === 'search' ? '#e3f2fd' : 'transparent',
                cursor: 'pointer'
              }}
            >
              Search {searchResults.length > 0 && `(${searchResults.length})`}
            </button>
          </div>
          {viewMode === 'conversations' ? (
            <>
              {loading ? (
                <LoadingSpinner message="Loading conversations..." />
              ) : error ? (
                <div style={{ padding: '16px' }}>
                  <ErrorMessage message={error} onRetry={loadConversations} />
                </div>
              ) : (
                <ConversationList
                  conversations={conversations}
                  selectedId={selectedId}
                  onSelect={handleSelectConversation}
                  onImport={onImport}
                />
              )}
            </>
          ) : (
            <>
              {searchLoading ? (
                <LoadingSpinner message="Searching..." />
              ) : searchError ? (
                <div style={{ padding: '16px' }}>
                  <ErrorMessage message={searchError} onRetry={performSearch} onDismiss={() => setSearchError(null)} />
                </div>
              ) : (
                <SearchResults
                  results={searchResults}
                  onSelect={handleSelectSearchHit}
                />
              )}
            </>
          )}
        </div>
        <div style={{ flex: 1, display: 'flex' }}>
          <MessageViewer 
            conversationId={selectedId} 
            highlightMessageId={highlightMessageId}
          />
          <div style={{ width: '300px', borderLeft: '1px solid #e0e0e0' }}>
            <Inspector conversationId={selectedId} />
          </div>
        </div>
      </div>
      {showJobs && <JobsModal onClose={() => setShowJobs(false)} />}
    </div>
  )
}

