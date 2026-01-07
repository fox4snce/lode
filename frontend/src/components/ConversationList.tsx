import React from 'react'
import EmptyState from './EmptyState'

interface Conversation {
  conversation_id: string
  title: string | null
  create_time: number | null
  message_count: number
  tags: string[]
}

interface Props {
  conversations: Conversation[]
  selectedId: string | null
  onSelect: (id: string) => void
  onImport?: () => void
}

export default function ConversationList({ conversations, selectedId, onSelect, onImport }: Props) {
  const formatDate = (timestamp: number | null) => {
    if (!timestamp) return 'Unknown'
    return new Date(timestamp * 1000).toLocaleDateString()
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
      {conversations.length === 0 ? (
        <EmptyState
          icon="📂"
          title="No conversations"
          message="Import your first conversation to get started."
          action={onImport ? { label: 'Import Conversations', onClick: onImport } : undefined}
        />
      ) : (
        conversations.map(conv => (
          <div
            key={conv.conversation_id}
            onClick={() => onSelect(conv.conversation_id)}
            style={{
              padding: '12px',
              borderRadius: '4px',
              marginBottom: '4px',
              cursor: 'pointer',
              backgroundColor: selectedId === conv.conversation_id ? '#e3f2fd' : 'transparent',
              borderLeft: selectedId === conv.conversation_id ? '3px solid #0066cc' : 'none'
            }}
          >
            <div style={{ fontWeight: 500, marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {conv.title || '(no title)'}
            </div>
            <div style={{ fontSize: '12px', color: '#666', display: 'flex', gap: '8px' }}>
              <span>{conv.message_count} msgs</span>
              <span>{formatDate(conv.create_time)}</span>
            </div>
            {conv.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '4px' }}>
                {conv.tags.map(tag => (
                  <span key={tag} style={{ padding: '2px 6px', background: '#e3f2fd', color: '#0066cc', borderRadius: '3px', fontSize: '11px' }}>
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  )
}

