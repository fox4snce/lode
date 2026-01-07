import React from 'react'

interface Props {
  message: string
  onRetry?: () => void
  onDismiss?: () => void
}

export default function ErrorMessage({ message, onRetry, onDismiss }: Props) {
  return (
    <div style={{
      padding: '16px',
      backgroundColor: '#ffebee',
      border: '1px solid #f44336',
      borderRadius: '4px',
      color: '#c62828',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '12px'
    }}>
      <div style={{ flex: 1 }}>
        <strong style={{ display: 'block', marginBottom: '4px' }}>Error</strong>
        <div style={{ fontSize: '14px' }}>{message}</div>
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              padding: '6px 12px',
              backgroundColor: '#f44336',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              padding: '6px 12px',
              backgroundColor: 'transparent',
              color: '#c62828',
              border: '1px solid #c62828',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  )
}

