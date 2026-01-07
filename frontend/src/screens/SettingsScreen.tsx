import React, { useState, useEffect } from 'react'
import { 
  runIntegrityChecks, 
  findDuplicateMessages, 
  findDuplicateConversations, 
  getDeduplicationStats,
  listImportedFiles,
  wipeImportedFiles
} from '../api'

interface Props {
  onClose: () => void
}

export default function SettingsScreen({ onClose }: Props) {
  const [activeTab, setActiveTab] = useState<'integrity' | 'deduplication' | 'cleanup' | 'encryption'>('integrity')
  const [integrityResults, setIntegrityResults] = useState<any>(null)
  const [duplicateMessages, setDuplicateMessages] = useState<any[]>([])
  const [duplicateConversations, setDuplicateConversations] = useState<any[]>([])
  const [dedupStats, setDedupStats] = useState<any>(null)
  const [importedFiles, setImportedFiles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (activeTab === 'cleanup') {
      loadImportedFiles()
    } else if (activeTab === 'deduplication') {
      loadDeduplicationStats()
    }
  }, [activeTab])

  const runIntegrity = async () => {
    setLoading(true)
    setError(null)
    try {
      const results = await runIntegrityChecks()
      setIntegrityResults(results)
    } catch (err: any) {
      setError(err.message || 'Failed to run integrity checks')
    } finally {
      setLoading(false)
    }
  }

  const findDuplicates = async () => {
    setLoading(true)
    setError(null)
    try {
      const [messages, conversations] = await Promise.all([
        findDuplicateMessages(),
        findDuplicateConversations()
      ])
      setDuplicateMessages(messages)
      setDuplicateConversations(conversations)
    } catch (err: any) {
      setError(err.message || 'Failed to find duplicates')
    } finally {
      setLoading(false)
    }
  }

  const loadDeduplicationStats = async () => {
    try {
      const stats = await getDeduplicationStats()
      setDedupStats(stats)
    } catch (err: any) {
      console.error('Failed to load deduplication stats:', err)
    }
  }

  const loadImportedFiles = async () => {
    setLoading(true)
    setError(null)
    try {
      const files = await listImportedFiles()
      setImportedFiles(files || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load imported files')
    } finally {
      setLoading(false)
    }
  }

  const handleWipeFiles = async (dryRun: boolean = false) => {
    if (!dryRun && !confirm('Are you sure you want to delete imported files? This cannot be undone.')) {
      return
    }

    setLoading(true)
    setError(null)
    try {
      const result = await wipeImportedFiles(undefined, true, dryRun)
      alert(dryRun 
        ? `Dry run: Would delete ${result.deleted?.length || 0} files`
        : `Deleted ${result.deleted?.length || 0} files`
      )
      loadImportedFiles()
    } catch (err: any) {
      setError(err.message || 'Failed to wipe files')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Database Management</h1>
        <button 
          onClick={onClose}
          style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid #e0e0e0', paddingBottom: '12px' }}>
        {(['integrity', 'deduplication', 'cleanup', 'encryption'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #0066cc' : '2px solid transparent',
              background: 'transparent',
              cursor: 'pointer',
              textTransform: 'capitalize',
              fontWeight: activeTab === tab ? 'bold' : 'normal',
              color: activeTab === tab ? '#0066cc' : '#666'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ padding: '12px', background: '#ffebee', border: '1px solid #f44336', borderRadius: '4px', marginBottom: '20px', color: '#c62828' }}>
          Error: {error}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: '4px', padding: '20px', background: 'white' }}>
        {activeTab === 'integrity' && (
          <div>
            <h3 style={{ marginBottom: '16px' }}>Integrity Checks</h3>
            <button
              onClick={runIntegrity}
              disabled={loading}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '4px',
                background: loading ? '#ccc' : '#0066cc',
                color: 'white',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                marginBottom: '20px'
              }}
            >
              {loading ? 'Running...' : 'Run All Checks'}
            </button>

            {integrityResults && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {Object.entries(integrityResults).map(([key, value]: [string, any]) => {
                  if (key === 'summary') continue
                  const count = Array.isArray(value) ? value.length : (value?.count || 0)
                  const status = count === 0 ? '✓' : '⚠'
                  const color = count === 0 ? '#4caf50' : '#ff9800'
                  
                  return (
                    <div key={key} style={{ padding: '12px', background: '#f9f9f9', borderRadius: '4px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color, fontWeight: 'bold' }}>{status}</span>
                        <span style={{ textTransform: 'capitalize', marginLeft: '8px' }}>
                          {key.replace(/_/g, ' ')}: {count}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'deduplication' && (
          <div>
            <h3 style={{ marginBottom: '16px' }}>Deduplication</h3>
            {dedupStats && (
              <div style={{ padding: '12px', background: '#f9f9f9', borderRadius: '4px', marginBottom: '16px' }}>
                <div><strong>Total Messages:</strong> {dedupStats.total_messages || 0}</div>
                <div><strong>Unique Messages:</strong> {dedupStats.unique_messages || 0}</div>
                <div><strong>Duplicate Groups:</strong> {dedupStats.duplicate_groups || 0}</div>
              </div>
            )}
            <button
              onClick={findDuplicates}
              disabled={loading}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '4px',
                background: loading ? '#ccc' : '#0066cc',
                color: 'white',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                marginBottom: '20px'
              }}
            >
              {loading ? 'Finding...' : 'Find Duplicates'}
            </button>

            {duplicateMessages.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4>Duplicate Messages ({duplicateMessages.length})</h4>
                <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: '4px', padding: '8px' }}>
                  {duplicateMessages.slice(0, 20).map((dup, idx) => (
                    <div key={idx} style={{ padding: '8px', fontSize: '12px', borderBottom: '1px solid #f0f0f0' }}>
                      {dup.conversation_id} / {dup.message_id}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {duplicateConversations.length > 0 && (
              <div>
                <h4>Duplicate Conversations ({duplicateConversations.length})</h4>
                <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: '4px', padding: '8px' }}>
                  {duplicateConversations.slice(0, 20).map((dup, idx) => (
                    <div key={idx} style={{ padding: '8px', fontSize: '12px', borderBottom: '1px solid #f0f0f0' }}>
                      {dup.conversation_id}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'cleanup' && (
          <div>
            <h3 style={{ marginBottom: '16px' }}>Cleanup</h3>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
              <button
                onClick={() => handleWipeFiles(true)}
                disabled={loading}
                style={{
                  padding: '8px 16px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  background: 'white',
                  cursor: loading ? 'not-allowed' : 'pointer'
                }}
              >
                Dry Run
              </button>
              <button
                onClick={() => handleWipeFiles(false)}
                disabled={loading}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  background: loading ? '#ccc' : '#f44336',
                  color: 'white',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold'
                }}
              >
                {loading ? 'Wiping...' : 'Wipe Imported Files'}
              </button>
            </div>

            <h4>Imported Files ({importedFiles.length})</h4>
            <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: '4px', padding: '8px' }}>
              {importedFiles.length === 0 ? (
                <div style={{ color: '#666', padding: '20px', textAlign: 'center' }}>No imported files found</div>
              ) : (
                importedFiles.map((file, idx) => (
                  <div key={idx} style={{ padding: '8px', fontSize: '12px', borderBottom: '1px solid #f0f0f0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>{file.source_file}</span>
                      <span style={{ color: file.exists ? '#4caf50' : '#f44336' }}>
                        {file.exists ? 'EXISTS' : 'MISSING'}
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                      {file.import_batch_id} • {file.status}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'encryption' && (
          <div>
            <h3 style={{ marginBottom: '16px' }}>Encryption</h3>
            <div style={{ padding: '20px', background: '#f9f9f9', borderRadius: '4px', color: '#666' }}>
              <p>Database encryption is not yet implemented.</p>
              <p>For now, you can use SQLCipher or file-level encryption tools.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
