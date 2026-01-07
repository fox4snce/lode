import React, { useState, useRef } from 'react'
import { createImportJob, getJob } from '../api'
import JobsModal from '../components/JobsModal'

interface Props {
  onClose: () => void
  onImportComplete?: () => void
}

export default function ImportScreen({ onClose, onImportComplete }: Props) {
  const [sourceType, setSourceType] = useState<'openai' | 'claude'>('openai')
  const [filePath, setFilePath] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [calculateStats, setCalculateStats] = useState(true)
  const [buildIndex, setBuildIndex] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showJobs, setShowJobs] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleBrowse = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setFilePath(selectedFile.name)
    }
  }

  const handleImport = async () => {
    if (!file && !filePath) {
      setError('Please select a file')
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      // If we have a File object, we need to upload it first
      // For now, assume filePath is a local path (pywebview context)
      const path = file ? file.name : filePath
      
      const { job_id } = await createImportJob({
        source_type: sourceType,
        file_path: path,
        calculate_stats: calculateStats,
        build_index: buildIndex
      })
      
      setJobId(job_id)
      setShowJobs(true)
      
      // Poll job status
      pollJobStatus(job_id)
    } catch (err: any) {
      setError(err.message || 'Failed to start import')
      setLoading(false)
    }
  }

  const pollJobStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await getJob(id)
        
        if (job.status === 'completed') {
          clearInterval(interval)
          setLoading(false)
          // Wait a moment then close
          setTimeout(() => {
            if (onImportComplete) {
              onImportComplete()
            }
            onClose()
          }, 2000)
        } else if (job.status === 'failed') {
          clearInterval(interval)
          setLoading(false)
          setError(job.error || 'Import failed')
        }
      } catch (err) {
        console.error('Error polling job:', err)
        clearInterval(interval)
        setLoading(false)
      }
    }, 1000) // Poll every second
  }

  return (
    <div style={{ padding: '40px', maxWidth: '600px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '30px' }}>Import Conversations</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
          Source Type:
        </label>
        <div>
          <label style={{ marginRight: '20px' }}>
            <input
              type="radio"
              value="openai"
              checked={sourceType === 'openai'}
              onChange={(e) => setSourceType(e.target.value as 'openai')}
              style={{ marginRight: '8px' }}
            />
            OpenAI (ChatGPT)
          </label>
          <label>
            <input
              type="radio"
              value="claude"
              checked={sourceType === 'claude'}
              onChange={(e) => setSourceType(e.target.value as 'claude')}
              style={{ marginRight: '8px' }}
            />
            Claude
          </label>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
          File:
        </label>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept=".json"
          style={{ display: 'none' }}
        />
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            placeholder="Select JSON file..."
            style={{
              flex: 1,
              padding: '8px',
              border: '1px solid #ddd',
              borderRadius: '4px'
            }}
          />
          <button 
            onClick={handleBrowse}
            style={{
              padding: '8px 16px',
              backgroundColor: '#f5f5f5',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Browse...
          </button>
        </div>
        {file && (
          <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
            Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
          </div>
        )}
      </div>

      <div style={{ marginBottom: '30px' }}>
        <label style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
          <input
            type="checkbox"
            checked={calculateStats}
            onChange={(e) => setCalculateStats(e.target.checked)}
            style={{ marginRight: '8px' }}
          />
          Calculate statistics after import
        </label>
        <label style={{ display: 'flex', alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={buildIndex}
            onChange={(e) => setBuildIndex(e.target.checked)}
            style={{ marginRight: '8px' }}
          />
          Build search index
        </label>
      </div>

      {error && (
        <p style={{ color: '#d32f2f', marginBottom: '20px' }}>{error}</p>
      )}

      <div style={{ display: 'flex', gap: '12px' }}>
        <button
          onClick={handleImport}
          disabled={loading || !filePath}
          style={{
            padding: '10px 20px',
            backgroundColor: '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Starting Import...' : 'Import'}
        </button>
        <button
          onClick={onClose}
          style={{
            padding: '10px 20px',
            backgroundColor: '#f5f5f5',
            border: '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Cancel
        </button>
      </div>

      {showJobs && jobId && (
        <JobsModal 
          onClose={() => {
            if (!loading) {
              setShowJobs(false)
            }
          }}
          initialJobId={jobId}
        />
      )}
    </div>
  )
}

