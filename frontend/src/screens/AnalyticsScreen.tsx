import React, { useState, useEffect } from 'react'
import { 
  getUsageOverTime, 
  getLongestStreak, 
  getTopWords, 
  getTopPhrases, 
  getVocabularyTrend, 
  getResponseRatio, 
  getTimeOfDayHeatmap 
} from '../api'

interface Props {
  onClose: () => void
}

type TabType = 'usage' | 'streaks' | 'words' | 'phrases' | 'vocabulary' | 'ratios' | 'heatmap'

export default function AnalyticsScreen({ onClose }: Props) {
  const [activeTab, setActiveTab] = useState<TabType>('usage')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('day')

  useEffect(() => {
    loadData()
  }, [activeTab, period])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      let result
      switch (activeTab) {
        case 'usage':
          result = await getUsageOverTime({ period })
          break
        case 'streaks':
          result = await getLongestStreak()
          break
        case 'words':
          result = await getTopWords(50)
          break
        case 'phrases':
          result = await getTopPhrases(30)
          break
        case 'vocabulary':
          result = await getVocabularyTrend(period)
          break
        case 'ratios':
          result = await getResponseRatio()
          break
        case 'heatmap':
          result = await getTimeOfDayHeatmap()
          break
        default:
          result = null
      }
      setData(result)
    } catch (err: any) {
      setError(err.message || 'Failed to load analytics')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString()
    } catch {
      return dateStr
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Analytics</h1>
        <button 
          onClick={onClose}
          style={{ padding: '8px 16px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap', borderBottom: '1px solid #e0e0e0', paddingBottom: '12px' }}>
        {(['usage', 'streaks', 'words', 'phrases', 'vocabulary', 'ratios', 'heatmap'] as TabType[]).map(tab => (
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
        {(activeTab === 'usage' || activeTab === 'vocabulary') && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label>Period:</label>
            <select 
              value={period} 
              onChange={(e) => setPeriod(e.target.value as 'day' | 'week' | 'month')}
              style={{ padding: '4px 8px', border: '1px solid #ddd', borderRadius: '4px' }}
            >
              <option value="day">Day</option>
              <option value="week">Week</option>
              <option value="month">Month</option>
            </select>
          </div>
        )}
      </div>

      {error && (
        <div style={{ padding: '12px', background: '#ffebee', border: '1px solid #f44336', borderRadius: '4px', marginBottom: '20px', color: '#c62828' }}>
          Error: {error}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', border: '1px solid #e0e0e0', borderRadius: '4px', padding: '16px', background: 'white' }}>
        {loading ? (
          <div>Loading...</div>
        ) : !data ? (
          <div style={{ color: '#666', textAlign: 'center', padding: '40px' }}>No data available</div>
        ) : (
          <>
            {activeTab === 'usage' && Array.isArray(data) && (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                    <th style={{ padding: '8px', textAlign: 'left' }}>Period</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Messages</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Conversations</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row: any, idx: number) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '8px' }}>{row.period || formatDate(row.date || '')}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{row.message_count || row.messages || 0}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{row.conversation_count || row.conversations || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {activeTab === 'streaks' && (
              <div>
                <h3>Longest Streak</h3>
                <div style={{ padding: '16px', background: '#f5f5f5', borderRadius: '4px', marginTop: '12px' }}>
                  <div><strong>Days:</strong> {data.days || data.length || 0}</div>
                  {data.start_date && <div><strong>Start:</strong> {formatDate(data.start_date)}</div>}
                  {data.end_date && <div><strong>End:</strong> {formatDate(data.end_date)}</div>}
                </div>
              </div>
            )}

            {(activeTab === 'words' || activeTab === 'phrases') && Array.isArray(data) && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {data.map((item: any, idx: number) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', background: '#f9f9f9', borderRadius: '4px' }}>
                    <span><strong>{item.word || item.phrase || item.text}</strong></span>
                    <span>{item.count || item.frequency || 0}</span>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'vocabulary' && Array.isArray(data) && (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                    <th style={{ padding: '8px', textAlign: 'left' }}>Period</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Unique Words</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row: any, idx: number) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '8px' }}>{row.period || formatDate(row.date || '')}</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{row.vocabulary_size || row.unique_words || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {activeTab === 'ratios' && (
              <div>
                <h3>Response Ratios</h3>
                <div style={{ padding: '16px', background: '#f5f5f5', borderRadius: '4px', marginTop: '12px' }}>
                  <div><strong>User Messages:</strong> {data.user_messages || data.user || 0}</div>
                  <div><strong>Assistant Messages:</strong> {data.assistant_messages || data.assistant || 0}</div>
                  {data.ratio && <div><strong>Ratio:</strong> {data.ratio.toFixed(2)}</div>}
                </div>
              </div>
            )}

            {activeTab === 'heatmap' && Array.isArray(data) && (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
                    <th style={{ padding: '8px', textAlign: 'left' }}>Hour</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Messages</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row: any, idx: number) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '8px' }}>{row.hour || idx}:00</td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>{row.count || row.messages || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </div>
  )
}
