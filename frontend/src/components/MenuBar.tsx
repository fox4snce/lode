import React from 'react'

interface Props {
  onImport: () => void
  onExport: () => void
  onAnalytics: () => void
  onFindTools: () => void
  onImportReports: () => void
  onSettings: () => void
  onAbout?: () => void
}

export default function MenuBar({ 
  onImport, 
  onExport, 
  onAnalytics, 
  onFindTools, 
  onImportReports, 
  onSettings,
  onAbout
}: Props) {
  const menuItemStyle: React.CSSProperties = {
    padding: '6px 12px',
    cursor: 'pointer',
    fontSize: '13px',
    border: '1px solid #ccc',
    background: 'transparent',
    color: '#333',
    borderRadius: '3px',
    margin: '0 2px',
    transition: 'all 0.2s'
  }

  const menuLabelStyle: React.CSSProperties = {
    ...menuItemStyle,
    fontWeight: '600',
    color: '#666',
    cursor: 'default',
    border: 'none',
    background: 'transparent',
    marginRight: '8px'
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      borderBottom: '1px solid #e0e0e0',
      backgroundColor: '#f8f8f8',
      padding: '4px 12px',
      minHeight: '32px',
      boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
      zIndex: 1000,
      position: 'relative',
      width: '100%'
    }}>
      <div style={menuLabelStyle}>File</div>
      <button 
        style={menuItemStyle}
        onClick={onImport}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#e8f4f8'
          e.currentTarget.style.borderColor = '#0066cc'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
          e.currentTarget.style.borderColor = '#ccc'
        }}
      >
        Import...
      </button>
      <button 
        style={menuItemStyle}
        onClick={onExport}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#e8f4f8'
          e.currentTarget.style.borderColor = '#0066cc'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
          e.currentTarget.style.borderColor = '#ccc'
        }}
      >
        Export...
      </button>
      
      <div style={{ ...menuLabelStyle, marginLeft: '16px' }}>View</div>
      <button 
        style={menuItemStyle}
        onClick={onAnalytics}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#e8f4f8'
          e.currentTarget.style.borderColor = '#0066cc'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
          e.currentTarget.style.borderColor = '#ccc'
        }}
      >
        Analytics
      </button>
      <button 
        style={menuItemStyle}
        onClick={onImportReports}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#e8f4f8'
          e.currentTarget.style.borderColor = '#0066cc'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
          e.currentTarget.style.borderColor = '#ccc'
        }}
      >
        Import Reports
      </button>
      <button 
        style={menuItemStyle}
        onClick={onFindTools}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#e8f4f8'
          e.currentTarget.style.borderColor = '#0066cc'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
          e.currentTarget.style.borderColor = '#ccc'
        }}
      >
        Find Tools
      </button>
      
      <div style={{ ...menuLabelStyle, marginLeft: '16px' }}>Tools</div>
      <button 
        style={menuItemStyle}
        onClick={onSettings}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#e8f4f8'
          e.currentTarget.style.borderColor = '#0066cc'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
          e.currentTarget.style.borderColor = '#ccc'
        }}
      >
        Settings
      </button>
      
      <div style={{ ...menuLabelStyle, marginLeft: '16px' }}>Help</div>
      {onAbout && (
        <button 
          style={menuItemStyle}
          onClick={onAbout}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#e8f4f8'
            e.currentTarget.style.borderColor = '#0066cc'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent'
            e.currentTarget.style.borderColor = '#ccc'
          }}
        >
          About
        </button>
      )}
    </div>
  )
}


