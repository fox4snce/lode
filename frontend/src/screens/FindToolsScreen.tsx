import React, { useState, useEffect } from 'react'
import { findCodeBlocks, findLinks, findTodos, findQuestions, findDates, findDecisions, findPrompts } from '../api'

interface Props {
  onClose: () => void
}

type ToolType = 'code' | 'links' | 'todos' | 'questions' | 'dates' | 'decisions' | 'prompts'

export default function FindToolsScreen({ onClose }: Props) {
  const [selectedTool, setSelectedTool] = useState<ToolType>('code')
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const tools: { id: ToolType; label: string; apiFn: (limit?: number) => Promise<any[]> }[] = [
    { id: 'code', label: 'Code Blocks', apiFn: findCodeBlocks },
    { id: 'links', label: 'Links', apiFn: findLinks },
    { id: 'todos', label: 'TODOs', apiFn: findTodos },
    { id: 'questions', label: 'Questions', apiFn: findQuestions },
    { id: 'dates', label: 'Dates', apiFn: findDates },
    { id: 'decisions', label: 'Decisions', apiFn: findDecisions },
    { id: 'prompts', label: 'Prompts', apiFn: findPrompts }
  ]

  useEffect(() => {
    loadResults()
  }, [selectedTool])

  const loadResults = async () => {
    setLoading(true)
    setError(null)
    try {
      const tool = tools.find(t => t.id === selectedTool)
      if (tool) {
        const data = await tool.apiFn(100)
        // Handle links which returns {links: [], ...} instead of array
        if (selectedTool === 'links' && data && typeof data === 'object' && 'links' in data) {
          setResults(data.links || [])
        } else if (Array.isArray(data)) {
          setResults(data)
        } else {
          setResults([])
        }
      }
    } catch (err: any) {
      console.error('Error loading results:', err)
      setError(err.message || 'Failed to load results')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (timestamp: number | null) => {
    if (!timestamp) return 'No date'
    return new Date(timestamp * 1000).toLocaleString()
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Find Tools</h1>
        <button 
          onClick={onClose}
          style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>
      
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {tools.map(tool => (
          <button
            key={tool.id}
            onClick={() => setSelectedTool(tool.id)}
            style={{
              padding: '8px 16px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              background: selectedTool === tool.id ? '#e3f2fd' : 'white',
              cursor: 'pointer',
              fontWeight: selectedTool === tool.id ? 'bold' : 'normal'
            }}
          >
            {tool.label} {results.length > 0 && selectedTool === tool.id && `(${results.length})`}
          </button>
        ))}
      </div>
      
      {error && (
        <div style={{ padding: '12px', background: '#ffebee', border: '1px solid #f44336', borderRadius: '4px', marginBottom: '20px', color: '#c62828' }}>
          Error: {error}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: '4px', padding: '16px', background: 'white' }}>
        {loading ? (
          <div>Loading...</div>
        ) : results.length === 0 ? (
          <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>
            No {tools.find(t => t.id === selectedTool)?.label.toLowerCase()} found
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {results.map((result, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  border: '1px solid #e0e0e0',
                  borderRadius: '4px',
                  background: '#f9f9f9'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '12px', color: '#666' }}>
                  <span>Conversation: {result.conversation_id?.substring(0, 40)}...</span>
                  <span>{formatDate(result.create_time)}</span>
                </div>
                {selectedTool === 'code' && (
                  <div>
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Language: {result.language || 'plain'}</div>
                    <pre style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px', overflow: 'auto', fontSize: '12px' }}>
                      {result.code}
                    </pre>
                  </div>
                )}
                {selectedTool === 'links' && (
                  <div>
                    {result.url ? (
                      <a href={result.url} target="_blank" rel="noopener noreferrer" style={{ color: '#0066cc', wordBreak: 'break-all' }}>
                        {result.url}
                      </a>
                    ) : (
                      <span style={{ color: '#999' }}>No URL</span>
                    )}
                    {result.domain && <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>Domain: {result.domain}</div>}
                  </div>
                )}
                {(selectedTool === 'todos' || selectedTool === 'questions' || selectedTool === 'dates' || selectedTool === 'decisions' || selectedTool === 'prompts') && (
                  <div style={{ fontSize: '14px' }}>
                    {result.match && <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{result.match}</div>}
                    {result.context && (
                      <div style={{ color: '#666', fontSize: '13px', marginTop: '4px' }}>
                        {result.context.substring(0, 200)}...
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
