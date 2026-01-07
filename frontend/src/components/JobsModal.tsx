import React, { useState, useEffect } from 'react'
import { listJobs, getJob, cancelJob } from '../api'

interface Props {
  onClose: () => void
  initialJobId?: string | null
}

export default function JobsModal({ onClose, initialJobId }: Props) {
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (initialJobId) {
      // Scroll to or highlight the initial job
      const jobElement = document.getElementById(`job-${initialJobId}`)
      if (jobElement) {
        jobElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [initialJobId, jobs])

  const loadJobs = async () => {
    try {
      const data = await listJobs()
      setJobs(data)
    } catch (err) {
      console.error('Failed to load jobs:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (jobId: string) => {
    try {
      await cancelJob(jobId)
      loadJobs()
    } catch (err) {
      console.error('Failed to cancel job:', err)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'white',
          borderRadius: '8px',
          width: '90%',
          maxWidth: '600px',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: '16px', borderBottom: '1px solid #e0e0e0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Background Jobs</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer' }}>
            ×
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
          {loading ? (
            <div>Loading...</div>
          ) : jobs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>No jobs</div>
          ) : (
            jobs.map(job => (
              <div 
                id={`job-${job.id}`}
                key={job.id} 
                style={{ 
                  padding: '12px', 
                  border: '1px solid #e0e0e0', 
                  borderRadius: '4px', 
                  marginBottom: '8px',
                  background: initialJobId === job.id ? '#f0f7ff' : 'white'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 600 }}>{job.job_type}</span>
                  <span style={{
                    fontSize: '12px',
                    padding: '2px 6px',
                    borderRadius: '3px',
                    background: job.status === 'running' ? '#e3f2fd' : job.status === 'completed' ? '#e8f5e9' : '#fff3e0',
                    color: job.status === 'running' ? '#0066cc' : job.status === 'completed' ? '#2e7d32' : '#f57c00'
                  }}>
                    {job.status}
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: '#e0e0e0', borderRadius: '4px', overflow: 'hidden', marginBottom: '4px' }}>
                  <div style={{ width: `${job.progress}%`, height: '100%', background: '#0066cc', transition: 'width 0.3s' }} />
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                  {job.message || 'No message'}
                </div>
                {job.status === 'running' && (
                  <button
                    onClick={() => handleCancel(job.id)}
                    style={{
                      padding: '4px 8px',
                      fontSize: '12px',
                      background: '#f5f5f5',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

