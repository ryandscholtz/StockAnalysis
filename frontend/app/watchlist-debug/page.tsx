'use client'

import { useState } from 'react'
import { stockApi } from '@/lib/api'
import { WatchlistSimulation } from '@/lib/watchlist-simulation'

export default function WatchlistDebugPage() {
  const [logs, setLogs] = useState<string[]>([])
  const [error, setError] = useState<string>('')

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString()
    const logMessage = `[${timestamp}] ${message}`
    console.log(logMessage)
    setLogs(prev => [...prev, logMessage])
  }

  const testClientSideSimulation = () => {
    addLog('=== TESTING CLIENT-SIDE SIMULATION ===')
    setError('')
    
    try {
      addLog('Testing WatchlistSimulation.getWatchlist()...')
      const currentWatchlist = WatchlistSimulation.getWatchlist()
      addLog(`Current watchlist: ${JSON.stringify(currentWatchlist)}`)
      
      addLog('Testing WatchlistSimulation.addToWatchlist("KO", "Coca-Cola", "NYSE")...')
      const result = WatchlistSimulation.addToWatchlist('KO', 'The Coca-Cola Company', 'NYSE')
      addLog(`Simulation result: ${result}`)
      
      addLog('Checking watchlist after add...')
      const updatedWatchlist = WatchlistSimulation.getWatchlist()
      addLog(`Updated watchlist: ${JSON.stringify(updatedWatchlist)}`)
      
      addLog('✅ Client-side simulation test completed successfully')
    } catch (error: any) {
      addLog(`❌ Client-side simulation error: ${error.message}`)
      setError(error.message)
    }
  }

  const testApiCall = async () => {
    addLog('=== TESTING API CALL ===')
    setError('')
    
    try {
      addLog('Calling stockApi.addToWatchlist("KO", "The Coca-Cola Company", "NYSE")...')
      const result = await stockApi.addToWatchlist('KO', 'The Coca-Cola Company', 'NYSE')
      addLog(`API result: ${JSON.stringify(result)}`)
      
      if (result.success) {
        addLog('✅ API call returned success: true')
      } else {
        addLog('❌ API call returned success: false')
        setError(result.message || 'API returned success: false')
      }
    } catch (error: any) {
      addLog(`❌ API call threw exception: ${error.message}`)
      addLog(`Error details: ${JSON.stringify({
        name: error.name,
        message: error.message,
        code: error.code,
        stack: error.stack?.substring(0, 200)
      })}`)
      setError(error.message)
    }
  }

  const testFullFlow = async () => {
    addLog('=== TESTING FULL FLOW (like in add page) ===')
    setError('')
    
    try {
      const suggestion = {
        ticker: 'KO',
        companyName: 'The Coca-Cola Company',
        exchange: 'NYSE'
      }
      
      addLog(`Selected suggestion: ${JSON.stringify(suggestion)}`)
      addLog('Calling addToWatchlist...')
      
      const result = await stockApi.addToWatchlist(suggestion.ticker, suggestion.companyName, suggestion.exchange)
      addLog(`Result: ${JSON.stringify(result)}`)
      
      if (result.success) {
        addLog('✅ Full flow completed successfully - would redirect to /watchlist')
      } else {
        addLog('❌ Full flow failed - would show error message')
        setError(result.message || 'Failed to add to watchlist')
      }
    } catch (err: any) {
      addLog(`❌ Full flow threw exception: ${err.message}`)
      setError(err.message || 'Failed to add to watchlist')
    }
  }

  const clearLogs = () => {
    setLogs([])
    setError('')
  }

  const clearWatchlist = () => {
    addLog('Clearing watchlist...')
    WatchlistSimulation.clearWatchlist()
    addLog('✅ Watchlist cleared')
  }

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Watchlist Debug Page</h1>
      
      {error && (
        <div style={{
          padding: '12px',
          backgroundColor: '#fee2e2',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          color: '#991b1b',
          marginBottom: '20px'
        }}>
          ❌ {error}
        </div>
      )}

      <div style={{ marginBottom: '20px' }}>
        <button onClick={testClientSideSimulation} style={{ margin: '5px', padding: '10px 15px' }}>
          Test Client-Side Simulation
        </button>
        <button onClick={testApiCall} style={{ margin: '5px', padding: '10px 15px' }}>
          Test API Call
        </button>
        <button onClick={testFullFlow} style={{ margin: '5px', padding: '10px 15px' }}>
          Test Full Flow
        </button>
        <button onClick={clearWatchlist} style={{ margin: '5px', padding: '10px 15px' }}>
          Clear Watchlist
        </button>
        <button onClick={clearLogs} style={{ margin: '5px', padding: '10px 15px' }}>
          Clear Logs
        </button>
      </div>

      <div style={{
        backgroundColor: '#f8f9fa',
        border: '1px solid #dee2e6',
        borderRadius: '6px',
        padding: '15px',
        maxHeight: '400px',
        overflowY: 'auto',
        fontFamily: 'monospace',
        fontSize: '14px'
      }}>
        <h3>Debug Logs:</h3>
        {logs.length === 0 ? (
          <p style={{ color: '#6c757d' }}>No logs yet. Click a test button to start.</p>
        ) : (
          logs.map((log, index) => (
            <div key={index} style={{ marginBottom: '5px' }}>
              {log}
            </div>
          ))
        )}
      </div>
    </div>
  )
}