import React, { useState, useEffect } from 'react'
import { getMessages } from '../api'
import { marked } from 'marked'
import LoadingSpinner from './LoadingSpinner'
import EmptyState from './EmptyState'
import ErrorMessage from './ErrorMessage'

interface Props {
  conversationId: string | null
  highlightMessageId?: string | null
}

export default function MessageViewer({ conversationId, highlightMessageId }: Props) {
  const [messages, setMessages] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const viewerRef = React.useRef<HTMLDivElement>(null)
  const highlightedRef = React.useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!conversationId) {
      setMessages([])
      return
    }

    setLoading(true)
    setError(null)
    
    // If we have a highlightMessageId, get context around it
    if (highlightMessageId) {
      import('../api').then(({ getMessageContext }) => {
        getMessageContext(highlightMessageId, 10)
          .then(setMessages)
          .catch((err: any) => {
            setError(err.message || 'Failed to load message context')
            setMessages([])
          })
          .finally(() => setLoading(false))
      })
    } else {
      getMessages(conversationId, { limit: 200 })
        .then(setMessages)
        .catch((err: any) => {
          setError(err.message || 'Failed to load messages')
          setMessages([])
        })
        .finally(() => setLoading(false))
    }
  }, [conversationId, highlightMessageId])

  // Scroll to highlighted message when it loads
  useEffect(() => {
    if (highlightedRef.current && viewerRef.current) {
      highlightedRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [messages, highlightMessageId])

  const formatDate = (timestamp: number | null) => {
    if (!timestamp) return ''
    return new Date(timestamp * 1000).toLocaleString()
  }

  if (!conversationId) {
    return (
      <EmptyState
        icon="💬"
        title="No conversation selected"
        message="Select a conversation from the list to view messages."
      />
    )
  }

  if (loading) {
    return <LoadingSpinner message="Loading messages..." size="large" />
  }

  if (error) {
    return (
      <div style={{ padding: '20px' }}>
        <ErrorMessage message={error} onRetry={() => {
          if (highlightMessageId) {
            import('../api').then(({ getMessageContext }) => {
              getMessageContext(highlightMessageId, 10).then(setMessages).catch(console.error)
            })
          } else {
            getMessages(conversationId, { limit: 200 }).then(setMessages).catch(console.error)
          }
        }} />
      </div>
    )
  }

  return (
    <div 
      ref={viewerRef}
      style={{ flex: 1, overflowY: 'auto', padding: '16px', maxWidth: '800px', margin: '0 auto', width: '100%' }}
    >
      {messages.length === 0 ? (
        <EmptyState
          icon="📭"
          title="No messages"
          message="This conversation has no messages."
        />
      ) : (
        messages.map(msg => {
          const isHighlighted = msg.message_id === highlightMessageId
          return (
            <div
              key={msg.message_id}
              ref={isHighlighted ? highlightedRef : null}
              style={{
                marginBottom: '16px',
                padding: '12px',
                borderRadius: '4px',
                background: isHighlighted 
                  ? '#fff9c4' 
                  : msg.role === 'user' 
                    ? '#e3f2fd' 
                    : '#f5f5f5',
                border: isHighlighted ? '2px solid #fbc02d' : 'none',
                transition: 'all 0.3s'
              }}
            >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, fontSize: '12px', textTransform: 'uppercase', color: '#666' }}>
                {msg.role}
              </span>
              <span style={{ fontSize: '11px', color: '#999' }}>
                {formatDate(msg.create_time)}
              </span>
            </div>
            <div
              style={{ lineHeight: '1.6', whiteSpace: 'pre-wrap' }}
              dangerouslySetInnerHTML={{ __html: marked(msg.content) }}
            />
            </div>
          )
        })
      )}
    </div>
  )
}

