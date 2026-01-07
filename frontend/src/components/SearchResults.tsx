import React from 'react'
import { SearchHit } from '../api'
import EmptyState from './EmptyState'

interface Props {
  results: SearchHit[]
  onSelect: (hit: SearchHit) => void
}

export default function SearchResults({ results, onSelect }: Props) {
  const formatDate = (timestamp: number | null) => {
    if (!timestamp) return ''
    return new Date(timestamp * 1000).toLocaleString()
  }

  const truncate = (text: string, maxLength: number = 150) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  if (results.length === 0) {
    return (
      <EmptyState
        icon="🔍"
        title="No search results"
        message="Try adjusting your search query or check your spelling."
      />
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
      {results.map((hit, idx) => (
        <div
          key={`${hit.conversation_id}-${hit.message_id}-${idx}`}
          onClick={() => onSelect(hit)}
          style={{
            padding: '12px',
            borderRadius: '4px',
            marginBottom: '4px',
            cursor: 'pointer',
            background: '#f9f9f9',
            border: '1px solid #e0e0e0'
          }}
        >
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
            {hit.conversation_id}
          </div>
          <div style={{ fontWeight: 500, marginBottom: '4px' }}>
            {hit.role.toUpperCase()}
          </div>
          <div style={{ fontSize: '13px', color: '#333', marginBottom: '4px' }}>
            {truncate(hit.content)}
          </div>
          <div style={{ fontSize: '11px', color: '#999' }}>
            {formatDate(hit.create_time)}
          </div>
        </div>
      ))}
    </div>
  )
}

