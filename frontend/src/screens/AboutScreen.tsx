import React from 'react'

interface Props {
  onClose: () => void
}

export default function AboutScreen({ onClose }: Props) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '40px',
      backgroundColor: '#f8f8f8'
    }}>
      <div style={{
        maxWidth: '600px',
        width: '100%',
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '40px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <h1 style={{
          fontSize: '32px',
          fontWeight: 'bold',
          marginBottom: '8px',
          color: '#333',
          textAlign: 'center'
        }}>
          ChatVault
        </h1>
        
        <p style={{
          fontSize: '16px',
          color: '#666',
          textAlign: 'center',
          marginBottom: '32px'
        }}>
          Version 1.0.0 MVP
        </p>

        <div style={{
          marginBottom: '32px',
          lineHeight: '1.6',
          color: '#444'
        }}>
          <p style={{ marginBottom: '16px' }}>
            Lode is a desktop application for managing, searching, and organizing your AI conversation history.
          </p>
          <p style={{ marginBottom: '16px' }}>
            Import conversations from OpenAI (ChatGPT) and Claude, search through your entire history,
            organize with tags and notes, and analyze your usage patterns.
          </p>
          <p>
            Built with React, TypeScript, FastAPI, and SQLite.
          </p>
        </div>

        <div style={{
          borderTop: '1px solid #e0e0e0',
          borderBottom: '1px solid #e0e0e0',
          padding: '24px 0',
          marginBottom: '32px',
          textAlign: 'center'
        }}>
          <h2 style={{
            fontSize: '18px',
            fontWeight: '600',
            marginBottom: '16px',
            color: '#333'
          }}>
            Support Lode
          </h2>
          <p style={{
            marginBottom: '20px',
            color: '#666',
            fontSize: '14px'
          }}>
            If you find Lode useful, consider supporting development:
          </p>
          <a
            href="https://ko-fi.com/recursiverealms"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-block',
              padding: '12px 24px',
              backgroundColor: '#0066cc',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '6px',
              fontWeight: '500',
              fontSize: '16px',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#0052a3'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#0066cc'
            }}
          >
            ☕ Support on Ko-fi
          </a>
        </div>

        <div style={{
          textAlign: 'center',
          color: '#999',
          fontSize: '12px',
          marginBottom: '24px'
        }}>
          <p>© 2024 Lode</p>
          <p style={{ marginTop: '8px' }}>
            Made with ❤️ for managing AI conversations
          </p>
        </div>

        <div style={{ textAlign: 'center' }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 24px',
              backgroundColor: '#f0f0f0',
              color: '#333',
              border: '1px solid #ddd',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#e0e0e0'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#f0f0f0'
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

