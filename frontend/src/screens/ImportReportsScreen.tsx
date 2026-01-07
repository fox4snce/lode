import React, { useState, useEffect } from 'react'
import { listImportReports, getImportReport } from '../api'

interface Props {
  onClose: () => void
}

export default function ImportReportsScreen({ onClose }: Props) {
  const [reports, setReports] = useState<any[]>([])
  const [selectedReport, setSelectedReport] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listImportReports(50)
      setReports(data || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load import reports')
      setReports([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelectReport = async (batchId: string) => {
    setLoading(true)
    setError(null)
    try {
      const report = await getImportReport(batchId)
      setSelectedReport(report)
    } catch (err: any) {
      setError(err.message || 'Failed to load report details')
      setSelectedReport(null)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'No date'
    try {
      return new Date(dateStr).toLocaleString()
    } catch {
      return dateStr
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'success':
        return '#4caf50'
      case 'failed':
      case 'error':
        return '#f44336'
      case 'partial':
        return '#ff9800'
      default:
        return '#666'
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Import Reports</h1>
        <button 
          onClick={onClose}
          style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>

      {error && (
        <div style={{ padding: '12px', background: '#ffebee', border: '1px solid #f44336', borderRadius: '4px', marginBottom: '20px', color: '#c62828' }}>
          Error: {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: '20px', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '400px', borderRight: '1px solid #e0e0e0', paddingRight: '20px', overflowY: 'auto' }}>
          <h3 style={{ marginBottom: '12px' }}>Import History</h3>
          {loading && reports.length === 0 ? (
            <div>Loading...</div>
          ) : reports.length === 0 ? (
            <div style={{ color: '#666', padding: '20px', textAlign: 'center' }}>
              No import reports found
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {reports.map((report) => (
                <div
                  key={report.import_batch_id}
                  onClick={() => handleSelectReport(report.import_batch_id)}
                  style={{
                    padding: '12px',
                    border: '1px solid #e0e0e0',
                    borderRadius: '4px',
                    background: selectedReport?.import_batch_id === report.import_batch_id ? '#e3f2fd' : 'white',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                    {report.source_file || report.import_batch_id}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                    {formatDate(report.started_at)}
                  </div>
                  <div style={{ fontSize: '12px' }}>
                    <span style={{ color: getStatusColor(report.status || '') }}>
                      {report.status || 'Unknown'}
                    </span>
                    {report.conversations_imported !== undefined && (
                      <span style={{ marginLeft: '8px' }}>
                        • {report.conversations_imported} conversations
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', paddingLeft: '20px' }}>
          {selectedReport ? (
            <div>
              <h3 style={{ marginBottom: '16px' }}>Report Details</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ padding: '12px', background: '#f9f9f9', borderRadius: '4px' }}>
                  <div><strong>Batch ID:</strong> {selectedReport.import_batch_id}</div>
                  <div><strong>Source File:</strong> {selectedReport.source_file || 'N/A'}</div>
                  <div><strong>Import Type:</strong> {selectedReport.import_type || 'N/A'}</div>
                  <div><strong>Status:</strong> <span style={{ color: getStatusColor(selectedReport.status || '') }}>{selectedReport.status || 'Unknown'}</span></div>
                </div>

                <div style={{ padding: '12px', background: '#f9f9f9', borderRadius: '4px' }}>
                  <div><strong>Started:</strong> {formatDate(selectedReport.started_at)}</div>
                  {selectedReport.completed_at && (
                    <div><strong>Completed:</strong> {formatDate(selectedReport.completed_at)}</div>
                  )}
                  {selectedReport.conversations_imported !== undefined && (
                    <div><strong>Conversations Imported:</strong> {selectedReport.conversations_imported}</div>
                  )}
                  {selectedReport.conversations_failed !== undefined && (
                    <div><strong>Conversations Failed:</strong> {selectedReport.conversations_failed}</div>
                  )}
                  {selectedReport.messages_imported !== undefined && (
                    <div><strong>Messages Imported:</strong> {selectedReport.messages_imported}</div>
                  )}
                </div>

                {selectedReport.error_summary && (
                  <div style={{ padding: '12px', background: '#ffebee', borderRadius: '4px', border: '1px solid #f44336' }}>
                    <div><strong>Error Summary:</strong></div>
                    <pre style={{ marginTop: '8px', fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                      {selectedReport.error_summary}
                    </pre>
                  </div>
                )}

                {selectedReport.missing_fields && (
                  <div style={{ padding: '12px', background: '#fff3e0', borderRadius: '4px', border: '1px solid #ff9800' }}>
                    <div><strong>Missing Fields:</strong></div>
                    <div style={{ marginTop: '8px', fontSize: '13px' }}>
                      {Array.isArray(selectedReport.missing_fields) 
                        ? selectedReport.missing_fields.join(', ')
                        : selectedReport.missing_fields}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ color: '#666', padding: '40px', textAlign: 'center' }}>
              Select an import report to view details
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
