import React from 'react'

interface Props {
  searchQuery: string
  onSearchChange: (q: string) => void
  sort: string
  onSortChange: (sort: string) => void
  onJobsClick: () => void
  onImport: () => void
}

export default function TopBar({ searchQuery, onSearchChange, sort, onSortChange, onJobsClick, onImport }: Props) {
  return (
    <div style={{
      height: '60px',
      borderBottom: '1px solid #e0e0e0',
      display: 'flex',
      alignItems: 'center',
      padding: '0 16px',
      gap: '16px',
      backgroundColor: 'white'
    }}>
      <div style={{ flex: 1, maxWidth: '400px', position: 'relative' }}>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search conversations... (Ctrl+K)"
          style={{
            width: '100%',
            padding: '8px 12px',
            paddingRight: '80px',
            border: '1px solid #ddd',
            borderRadius: '4px'
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && searchQuery.trim()) {
              e.preventDefault()
              // Search will be triggered by useEffect
            }
          }}
        />
        <span style={{
          position: 'absolute',
          right: '12px',
          top: '50%',
          transform: 'translateY(-50%)',
          fontSize: '11px',
          color: '#999',
          pointerEvents: 'none'
        }}>
          Ctrl+K
        </span>
      </div>
      <select
        value={sort}
        onChange={(e) => onSortChange(e.target.value)}
        style={{
          padding: '8px 12px',
          border: '1px solid #ddd',
          borderRadius: '4px'
        }}
      >
        <option value="newest">Newest</option>
        <option value="oldest">Oldest</option>
        <option value="longest">Longest</option>
        <option value="most_messages">Most Messages</option>
      </select>
      <button onClick={onImport} style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}>
        Import
      </button>
      <button onClick={onJobsClick} style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}>
        Jobs
      </button>
    </div>
  )
}

