import React from 'react'

interface Props {
  icon?: string
  title: string
  message: string
  action?: {
    label: string
    onClick: () => void
  }
}

export default function EmptyState({ icon, title, message, action }: Props) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 20px',
      textAlign: 'center',
      color: '#666'
    }}>
      {icon && (
        <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }}>
          {icon}
        </div>
      )}
      <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', fontWeight: 500, color: '#333' }}>
        {title}
      </h3>
      <p style={{ margin: '0 0 24px 0', fontSize: '14px', maxWidth: '400px' }}>
        {message}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          style={{
            padding: '10px 20px',
            backgroundColor: '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 500
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

