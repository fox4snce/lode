import React, { useState, useEffect } from 'react'
import { 
  getConversation, 
  getTags, 
  addTag, 
  removeTag, 
  getNotes, 
  createNote, 
  getBookmarks, 
  createBookmark 
} from '../api'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'

interface Props {
  conversationId: string | null
}

type Tab = 'metadata' | 'tags' | 'notes' | 'bookmarks' | 'stats'

export default function Inspector({ conversationId }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('metadata')
  const [conversation, setConversation] = useState<any>(null)
  const [tags, setTags] = useState<string[]>([])
  const [notes, setNotes] = useState<any[]>([])
  const [bookmarks, setBookmarks] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [newTag, setNewTag] = useState('')
  const [newNote, setNewNote] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (conversationId) {
      loadData()
    } else {
      setConversation(null)
      setTags([])
      setNotes([])
      setBookmarks([])
      setStats(null)
    }
  }, [conversationId, activeTab])

  const loadData = async () => {
    if (!conversationId) return
    
    setLoading(true)
    setError(null)
    try {
      const conv = await getConversation(conversationId)
      setConversation(conv)
      
      if (activeTab === 'tags') {
        const tagList = await getTags(conversationId)
        setTags(tagList || [])
      } else if (activeTab === 'notes') {
        const noteList = await getNotes(conversationId)
        setNotes(noteList || [])
      } else if (activeTab === 'bookmarks') {
        const bookmarkList = await getBookmarks(conversationId)
        setBookmarks(bookmarkList || [])
      } else if (activeTab === 'stats') {
        // Stats are in conversation object
        setStats({
          message_count: conv.message_count || 0,
          word_count: conv.word_count || 0,
          create_time: conv.create_time,
          update_time: conv.update_time
        })
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleAddTag = async () => {
    if (!newTag.trim() || !conversationId) return
    
    try {
      await addTag(conversationId, newTag.trim())
      setNewTag('')
      loadData()
    } catch (err: any) {
      setError(err.message || 'Failed to add tag')
    }
  }

  const handleRemoveTag = async (tag: string) => {
    if (!conversationId) return
    
    try {
      await removeTag(conversationId, tag)
      loadData()
    } catch (err: any) {
      setError(err.message || 'Failed to remove tag')
    }
  }

  const handleAddNote = async () => {
    if (!newNote.trim() || !conversationId) return
    
    try {
      await createNote(conversationId, newNote.trim())
      setNewNote('')
      loadData()
    } catch (err: any) {
      setError(err.message || 'Failed to add note')
    }
  }

  const formatDate = (timestamp: number | null) => {
    if (!timestamp) return 'No date'
    return new Date(timestamp * 1000).toLocaleString()
  }

  if (!conversationId) {
    return (
      <div style={{ padding: '20px', color: '#999', textAlign: 'center' }}>
        No conversation selected
      </div>
    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', borderBottom: '1px solid #e0e0e0' }}>
        {(['metadata', 'tags', 'notes', 'bookmarks', 'stats'] as Tab[]).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              flex: 1,
              padding: '8px',
              border: 'none',
              background: activeTab === tab ? '#e3f2fd' : 'transparent',
              cursor: 'pointer',
              textTransform: 'capitalize',
              fontSize: '12px'
            }}
          >
            {tab}
          </button>
        ))}
      </div>
      
      {error && (
        <div style={{ padding: '8px' }}>
          <ErrorMessage message={error} onDismiss={() => setError(null)} onRetry={loadData} />
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {loading ? (
          <LoadingSpinner message="Loading..." />
        ) : (
          <>
            {activeTab === 'metadata' && conversation && (
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Metadata</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                  <div><strong>ID:</strong> <span style={{ color: '#666', fontFamily: 'monospace', fontSize: '11px' }}>{conversation.conversation_id}</span></div>
                  <div><strong>Title:</strong> {conversation.title || '(no title)'}</div>
                  <div><strong>Created:</strong> {formatDate(conversation.create_time)}</div>
                  {conversation.update_time && <div><strong>Updated:</strong> {formatDate(conversation.update_time)}</div>}
                  {conversation.ai_source && <div><strong>AI Source:</strong> {conversation.ai_source}</div>}
                  {conversation.is_starred && <div><strong>Starred:</strong> ✓</div>}
                </div>
              </div>
            )}

            {activeTab === 'tags' && (
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Tags</h3>
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '12px' }}>
                  {tags.map(tag => (
                    <span 
                      key={tag}
                      style={{ 
                        padding: '4px 8px', 
                        background: '#e3f2fd', 
                        color: '#0066cc', 
                        borderRadius: '3px', 
                        fontSize: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        style={{
                          border: 'none',
                          background: 'transparent',
                          color: '#0066cc',
                          cursor: 'pointer',
                          fontSize: '12px',
                          padding: '0 4px'
                        }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <input
                    type="text"
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                    placeholder="Add tag..."
                    style={{
                      flex: 1,
                      padding: '6px 8px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '12px'
                    }}
                  />
                  <button
                    onClick={handleAddTag}
                    style={{
                      padding: '6px 12px',
                      border: 'none',
                      background: '#0066cc',
                      color: 'white',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}
                  >
                    Add
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'notes' && (
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Notes</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                  {notes.length === 0 ? (
                    <div style={{ color: '#666', fontSize: '12px' }}>No notes yet</div>
                  ) : (
                    notes.map((note, idx) => (
                      <div 
                        key={idx}
                        style={{
                          padding: '8px',
                          background: '#f9f9f9',
                          borderRadius: '4px',
                          fontSize: '12px'
                        }}
                      >
                        {note.content || note.note}
                        {note.create_time && (
                          <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
                            {formatDate(note.create_time)}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <textarea
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add a note..."
                    rows={3}
                    style={{
                      padding: '6px 8px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '12px',
                      resize: 'vertical'
                    }}
                  />
                  <button
                    onClick={handleAddNote}
                    disabled={!newNote.trim()}
                    style={{
                      padding: '6px 12px',
                      border: 'none',
                      background: newNote.trim() ? '#0066cc' : '#ccc',
                      color: 'white',
                      borderRadius: '4px',
                      cursor: newNote.trim() ? 'pointer' : 'not-allowed',
                      fontSize: '12px',
                      alignSelf: 'flex-end'
                    }}
                  >
                    Add Note
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'bookmarks' && (
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Bookmarks</h3>
                {bookmarks.length === 0 ? (
                  <div style={{ color: '#666', fontSize: '12px' }}>No bookmarks yet</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {bookmarks.map((bookmark, idx) => (
                      <div 
                        key={idx}
                        style={{
                          padding: '8px',
                          background: '#f9f9f9',
                          borderRadius: '4px',
                          fontSize: '12px'
                        }}
                      >
                        <div style={{ fontWeight: 500 }}>Message: {bookmark.message_id?.substring(0, 20)}...</div>
                        {bookmark.note && <div style={{ color: '#666', marginTop: '4px' }}>{bookmark.note}</div>}
                        {bookmark.create_time && (
                          <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
                            {formatDate(bookmark.create_time)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'stats' && stats && (
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Statistics</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                  <div><strong>Messages:</strong> {stats.message_count || 0}</div>
                  <div><strong>Words:</strong> {stats.word_count || 0}</div>
                  {stats.create_time && <div><strong>Created:</strong> {formatDate(stats.create_time)}</div>}
                  {stats.update_time && <div><strong>Last Updated:</strong> {formatDate(stats.update_time)}</div>}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
