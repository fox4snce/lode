import React from 'react'

interface Props {
  size?: 'small' | 'medium' | 'large'
  message?: string
}

export default function LoadingSpinner({ size = 'medium', message }: Props) {
  const sizeMap = {
    small: '16px',
    medium: '24px',
    large: '32px'
  }

  const spinnerSize = sizeMap[size]

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      gap: '12px'
    }}>
      <div
        style={{
          width: spinnerSize,
          height: spinnerSize,
          border: `3px solid #e0e0e0`,
          borderTop: `3px solid #0066cc`,
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}
      />
      {message && (
        <div style={{ color: '#666', fontSize: '14px' }}>
          {message}
        </div>
      )}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

