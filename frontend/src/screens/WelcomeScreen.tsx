import React, { useState } from 'react'
import { initializeDatabase } from '../api'

interface Props {
  onInitialized: () => void
}

export default function WelcomeScreen({ onInitialized }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleInitialize = async () => {
    setLoading(true)
    setError(null)
    try {
      await initializeDatabase()
      onInitialized()
    } catch (err: any) {
      setError(err.message || 'Failed to initialize database')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      padding: '40px'
    }}>
      <h1 style={{ marginBottom: '20px', fontSize: '32px' }}>Lode</h1>
      <p style={{ marginBottom: '40px', color: '#666', textAlign: 'center', maxWidth: '400px' }}>
        Welcome! Let's get started by initializing the database.
      </p>
      <button
        onClick={handleInitialize}
        disabled={loading}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          backgroundColor: '#0066cc',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? 'Initializing...' : 'Initialize Database'}
      </button>
      {error && (
        <p style={{ marginTop: '20px', color: '#d32f2f' }}>{error}</p>
      )}
    </div>
  )
}

