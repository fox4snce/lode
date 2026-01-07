import React, { useState, useEffect } from 'react'
import { listConversations, exportConversation } from '../api'

interface Props {
  onClose: () => void
}

export default function ExportScreen({ onClose }: Props) {
  const [conversations, setConversations] = useState<any[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [format, setFormat] = useState<'markdown' | 'csv' | 'json'>('markdown')
  const [includeTimestamps, setIncludeTimestamps] = useState(true)
  const [includeMetadata, setIncludeMetadata] = useState(true)
  const [exportedContent, setExportedContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      const data = await listConversations({ sort: 'newest', limit: 100 })
      setConversations(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load conversations')
    }
  }

  const handleExport = async () => {
    if (!selectedId) {
      setError('Please select a conversation')
      return
    }

    setLoading(true)
    setError(null)
    setExportedContent(null)

    try {
      const result = await exportConversation(selectedId, format, includeTimestamps, includeMetadata)
      
      if (format === 'markdown' && result.content) {
        setExportedContent(result.content)
      } else {
        // For JSON/CSV, format it nicely
        setExportedContent(JSON.stringify(result, null, 2))
      }
    } catch (err: any) {
      setError(err.message || 'Failed to export conversation')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!exportedContent || !selectedId) return

    const blob = new Blob([exportedContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedId}.${format === 'markdown' ? 'md' : format === 'json' ? 'json' : 'csv'}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Export</h1>
        <button 
          onClick={onClose}
          style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>

      <div style={{ display: 'flex', gap: '20px', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '300px', borderRight: '1px solid #e0e0e0', paddingRight: '20px', overflowY: 'auto' }}>
          <h3 style={{ marginBottom: '12px' }}>Select Conversation</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {conversations.map(conv => (
              <button
                key={conv.conversation_id}
                onClick={() => setSelectedId(conv.conversation_id)}
                style={{
                  padding: '8px 12px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  background: selectedId === conv.conversation_id ? '#e3f2fd' : 'white',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '13px'
                }}
              >
                {conv.title || conv.conversation_id.substring(0, 40)}...
              </button>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ padding: '16px', border: '1px solid #e0e0e0', borderRadius: '4px', background: '#f9f9f9' }}>
            <h3 style={{ marginBottom: '12px' }}>Export Options</h3>
            
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>Format:</label>
              <select 
                value={format} 
                onChange={(e) => setFormat(e.target.value as 'markdown' | 'csv' | 'json')}
                style={{ padding: '6px 12px', border: '1px solid #ddd', borderRadius: '4px', width: '200px' }}
              >
                <option value="markdown">Markdown</option>
                <option value="json">JSON</option>
                <option value="csv">CSV</option>
              </select>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={includeTimestamps}
                  onChange={(e) => setIncludeTimestamps(e.target.checked)}
                />
                Include timestamps
              </label>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={includeMetadata}
                  onChange={(e) => setIncludeMetadata(e.target.checked)}
                />
                Include metadata
              </label>
            </div>

            <button
              onClick={handleExport}
              disabled={!selectedId || loading}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '4px',
                background: selectedId && !loading ? '#0066cc' : '#ccc',
                color: 'white',
                cursor: selectedId && !loading ? 'pointer' : 'not-allowed',
                fontWeight: 'bold'
              }}
            >
              {loading ? 'Exporting...' : 'Export'}
            </button>
          </div>

          {error && (
            <div style={{ padding: '12px', background: '#ffebee', border: '1px solid #f44336', borderRadius: '4px', color: '#c62828' }}>
              Error: {error}
            </div>
          )}

          {exportedContent && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid #e0e0e0', borderRadius: '4px' }}>
              <div style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f9f9f9' }}>
                <strong>Exported Content</strong>
                <button
                  onClick={handleDownload}
                  style={{
                    padding: '6px 12px',
                    border: '1px solid #0066cc',
                    borderRadius: '4px',
                    background: '#0066cc',
                    color: 'white',
                    cursor: 'pointer'
                  }}
                >
                  Download
                </button>
              </div>
              <pre style={{ flex: 1, overflow: 'auto', padding: '16px', margin: 0, background: 'white', fontSize: '12px' }}>
                {exportedContent}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
