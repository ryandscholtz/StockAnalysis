'use client'

import { useState, useEffect, useRef } from 'react'

export interface ApiLogEntry {
  id: string
  timestamp: Date
  type: 'request' | 'response' | 'error' | 'info'
  method?: string
  url?: string
  status?: number
  data?: any
  error?: any
  message?: string
}

interface DeveloperFeedbackProps {
  enabled?: boolean
}

export default function DeveloperFeedback({ enabled = true }: DeveloperFeedbackProps) {
  const [logs, setLogs] = useState<ApiLogEntry[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [groupDuplicates, setGroupDuplicates] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!enabled) return

    // Listen for custom API log events
    const handleApiLog = (event: CustomEvent<ApiLogEntry>) => {
      setLogs(prev => [...prev, event.detail])
    }

    window.addEventListener('api-log' as any, handleApiLog as EventListener)

    return () => {
      window.removeEventListener('api-log' as any, handleApiLog as EventListener)
    }
  }, [enabled])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const clearLogs = () => {
    setLogs([])
  }

  const exportLogs = () => {
    const logData = JSON.stringify(logs, null, 2)
    const blob = new Blob([logData], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `api-logs-${new Date().toISOString()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const copyAllLogs = async () => {
    try {
      // Format logs as readable text
      const formattedLogs = logs.map(log => {
        const lines = [
          `[${log.timestamp.toLocaleString()}] ${log.type.toUpperCase()}`,
          log.method && log.url ? `${log.method} ${log.url}` : '',
          log.status ? `Status: ${log.status}` : '',
          log.message ? `Message: ${log.message}` : '',
          log.error ? `Error: ${JSON.stringify(log.error, null, 2)}` : '',
          log.data ? `Data: ${JSON.stringify(log.data, null, 2)}` : '',
          '---'
        ].filter(Boolean)
        return lines.join('\n')
      }).join('\n\n')

      await navigator.clipboard.writeText(formattedLogs)
      
      // Show temporary success message
      const button = document.getElementById('copy-all-button')
      if (button) {
        const originalText = button.textContent
        button.textContent = '✓ Copied!'
        button.style.background = '#10b981'
        setTimeout(() => {
          button.textContent = originalText
          button.style.background = '#374151'
        }, 2000)
      }
    } catch (err) {
      console.error('Failed to copy logs:', err)
      // Fallback: try to copy JSON
      try {
        await navigator.clipboard.writeText(JSON.stringify(logs, null, 2))
        const button = document.getElementById('copy-all-button')
        if (button) {
          const originalText = button.textContent
          button.textContent = '✓ Copied!'
          button.style.background = '#10b981'
          setTimeout(() => {
            button.textContent = originalText
            button.style.background = '#374151'
          }, 2000)
        }
      } catch (fallbackErr) {
        console.error('Fallback copy also failed:', fallbackErr)
      }
    }
  }

  const getLogColor = (type: ApiLogEntry['type']) => {
    switch (type) {
      case 'request': return '#3b82f6' // blue
      case 'response': return '#10b981' // green
      case 'error': return '#ef4444' // red
      case 'info': return '#6b7280' // gray
      default: return '#6b7280'
    }
  }

  const formatData = (data: any): string => {
    if (!data) return ''
    try {
      if (typeof data === 'string') {
        try {
          const parsed = JSON.parse(data)
          return JSON.stringify(parsed, null, 2)
        } catch {
          return data
        }
      }
      return JSON.stringify(data, null, 2)
    } catch {
      return String(data)
    }
  }

  // Group duplicate requests
  const getGroupedLogs = () => {
    if (!groupDuplicates) return logs

    const grouped = new Map<string, ApiLogEntry[]>()
    logs.forEach(log => {
      // Create a key based on method, URL, and type
      const key = `${log.method || 'N/A'}|${log.url || 'N/A'}|${log.type}`
      if (!grouped.has(key)) {
        grouped.set(key, [])
      }
      grouped.get(key)!.push(log)
    })

    // Flatten grouped logs, marking duplicates
    const result: (ApiLogEntry & { isDuplicate?: boolean; duplicateCount?: number })[] = []
    grouped.forEach((group, key) => {
      if (group.length > 1) {
        // First occurrence shows count
        result.push({
          ...group[0],
          isDuplicate: false,
          duplicateCount: group.length
        })
        // Subsequent occurrences marked as duplicates
        group.slice(1).forEach(log => {
          result.push({
            ...log,
            isDuplicate: true
          })
        })
      } else {
        result.push(group[0])
      }
    })

    // Sort by original timestamp
    return result.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
  }

  const groupedLogs = getGroupedLogs()
  const duplicateCount = logs.length - new Set(logs.map(l => `${l.method}|${l.url}|${l.type}`)).size

  if (!enabled) return null

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 9999,
          background: '#1f2937',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          padding: '12px 20px',
          cursor: 'pointer',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
          fontSize: '14px',
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}
      >
        <span>🔍</span>
        <span>Dev Feedback</span>
        {logs.filter(l => l.type === 'error').length > 0 && (
          <span style={{
            background: '#ef4444',
            borderRadius: '50%',
            width: '20px',
            height: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '12px',
            marginLeft: '8px'
          }}>
            {logs.filter(l => l.type === 'error').length}
          </span>
        )}
      </button>

      {/* Panel */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '80px',
            right: '20px',
            width: '600px',
            maxHeight: '70vh',
            background: '#1f2937',
            border: '1px solid #374151',
            borderRadius: '8px',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)',
            zIndex: 9998,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          {/* Header */}
          <div style={{
            padding: '16px',
            borderBottom: '1px solid #374151',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: '#111827'
          }}>
            <div>
              <h3 style={{ margin: 0, color: 'white', fontSize: '16px', fontWeight: '600' }}>
                Developer Feedback
              </h3>
              <p style={{ margin: '4px 0 0 0', color: '#9ca3af', fontSize: '12px' }}>
                {logs.length} logs • {logs.filter(l => l.type === 'error').length} errors
                {logs.some(l => l.data?.issues && l.data.issues.length > 0) && (
                  <span style={{ color: '#f59e0b', marginLeft: '8px' }}>
                    ⚠️ {logs.filter(l => l.data?.issues && l.data.issues.length > 0).length} warnings
                  </span>
                )}
                {duplicateCount > 0 && (
                  <span style={{ color: '#fbbf24', marginLeft: '8px' }}>
                    🔄 {duplicateCount} duplicates
                  </span>
                )}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <label style={{ color: '#9ca3af', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  style={{ cursor: 'pointer' }}
                />
                Auto-scroll
              </label>
              <label style={{ color: '#9ca3af', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={groupDuplicates}
                  onChange={(e) => setGroupDuplicates(e.target.checked)}
                  style={{ cursor: 'pointer' }}
                />
                Group duplicates
              </label>
              <button
                onClick={copyAllLogs}
                id="copy-all-button"
                style={{
                  background: '#374151',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  transition: 'background 0.2s'
                }}
              >
                Copy All
              </button>
              <button
                onClick={clearLogs}
                style={{
                  background: '#374151',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Clear
              </button>
              <button
                onClick={exportLogs}
                style={{
                  background: '#374151',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Export
              </button>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'transparent',
                  color: '#9ca3af',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '18px',
                  padding: '0 8px'
                }}
              >
                ×
              </button>
            </div>
          </div>

          {/* Logs */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '8px',
            fontFamily: 'monospace',
            fontSize: '12px'
          }}>
            {groupedLogs.length === 0 ? (
              <div style={{ color: '#9ca3af', padding: '20px', textAlign: 'center' }}>
                No API logs yet. Make some API calls to see them here.
              </div>
            ) : (
              groupedLogs.map((log) => {
                const logWithDuplicates = log as ApiLogEntry & { isDuplicate?: boolean; duplicateCount?: number }
                return (
                <div
                  key={log.id}
                  style={{
                    marginBottom: '8px',
                    padding: '12px',
                    background: logWithDuplicates.isDuplicate ? '#0f172a' : '#111827',
                    borderRadius: '4px',
                    borderLeft: `3px solid ${getLogColor(log.type)}`,
                    opacity: logWithDuplicates.isDuplicate ? 0.7 : 1
                  }}
                >
                  {logWithDuplicates.duplicateCount && (
                    <div style={{
                      background: '#fbbf24',
                      color: '#78350f',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: '600',
                      marginBottom: '8px',
                      display: 'inline-block'
                    }}>
                      🔄 {logWithDuplicates.duplicateCount}x duplicate requests
                    </div>
                  )}
                  {logWithDuplicates.isDuplicate && (
                    <div style={{
                      color: '#9ca3af',
                      fontSize: '10px',
                      fontStyle: 'italic',
                      marginBottom: '4px'
                    }}>
                      (Duplicate - collapsed)
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        background: getLogColor(log.type),
                        color: 'white',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: '600',
                        textTransform: 'uppercase'
                      }}>
                        {log.type}
                      </span>
                      {log.method && (
                        <span style={{ color: '#9ca3af', fontSize: '11px' }}>
                          {log.method}
                        </span>
                      )}
                      {log.status && (
                        <span style={{
                          color: log.status >= 400 ? '#ef4444' : '#10b981',
                          fontSize: '11px',
                          fontWeight: '600'
                        }}>
                          {log.status}
                        </span>
                      )}
                    </div>
                    <span style={{ color: '#6b7280', fontSize: '11px' }}>
                      {log.timestamp.toLocaleTimeString()}
                    </span>
                  </div>

                  {log.url && (
                    <div style={{ color: '#60a5fa', marginBottom: '4px', wordBreak: 'break-all' }}>
                      {log.url}
                    </div>
                  )}

                  {log.message && (
                    <div style={{ color: '#e5e7eb', marginBottom: '4px' }}>
                      {log.message}
                    </div>
                  )}

                  {log.data?.issues && Array.isArray(log.data.issues) && log.data.issues.length > 0 && (
                    <div style={{
                      background: '#78350f',
                      border: '1px solid #f59e0b',
                      borderRadius: '4px',
                      padding: '8px',
                      marginTop: '8px',
                      marginBottom: '8px'
                    }}>
                      <div style={{ color: '#fbbf24', fontWeight: '600', marginBottom: '4px', fontSize: '11px' }}>
                        ⚠️ WARNINGS DETECTED:
                      </div>
                      {log.data.issues.map((issue: string, idx: number) => (
                        <div key={idx} style={{ color: '#fde68a', fontSize: '11px', marginTop: '4px' }}>
                          • {issue}
                        </div>
                      ))}
                    </div>
                  )}

                  {log.error && (
                    <details style={{ marginTop: '8px' }}>
                      <summary style={{ color: '#ef4444', cursor: 'pointer', marginBottom: '4px' }}>
                        Error Details
                      </summary>
                      <pre style={{
                        color: '#fca5a5',
                        background: '#1f2937',
                        padding: '8px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        fontSize: '11px',
                        margin: '4px 0 0 0'
                      }}>
                        {formatData(log.error)}
                      </pre>
                    </details>
                  )}

                  {log.data && (
                    <details style={{ marginTop: '8px' }}>
                      <summary style={{ color: '#9ca3af', cursor: 'pointer', marginBottom: '4px' }}>
                        {log.type === 'request' ? 'Request Data' : 'Response Data'}
                      </summary>
                      <pre style={{
                        color: '#d1d5db',
                        background: '#1f2937',
                        padding: '8px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        fontSize: '11px',
                        margin: '4px 0 0 0',
                        maxHeight: '200px'
                      }}>
                        {formatData(log.data)}
                      </pre>
                    </details>
                  )}
                </div>
                )
              })
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </>
  )
}

// Helper function to log API events
export function logApiEvent(entry: Omit<ApiLogEntry, 'id' | 'timestamp'>) {
  const fullEntry: ApiLogEntry = {
    ...entry,
    id: `${Date.now()}-${Math.random()}`,
    timestamp: new Date()
  }
  
  const event = new CustomEvent('api-log', { detail: fullEntry })
  window.dispatchEvent(event)
  
  // Also log to console for debugging
  console.log(`[API ${entry.type.toUpperCase()}]`, entry)
}

