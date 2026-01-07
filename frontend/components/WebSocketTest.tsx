'use client'

import React, { useState, useEffect, useRef } from 'react'

interface WebSocketMessage {
  type: string
  data?: any
  timestamp?: number
  message?: string
  connection_id?: string
  stream_id?: string
}

export default function WebSocketTest() {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [connectionId, setConnectionId] = useState<string>('')
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['AAPL', 'GOOGL'])
  const [analysisTicket, setAnalysisTicket] = useState<string>('AAPL')
  const wsRef = useRef<WebSocket | null>(null)

  const connectWebSocket = () => {
    const clientId = `client_${Date.now()}`
    const wsUrl = `ws://localhost:8000/api/ws/${clientId}`
    
    wsRef.current = new WebSocket(wsUrl)
    
    wsRef.current.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected')
    }
    
    wsRef.current.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        setMessages(prev => [...prev, message])
        
        if (message.type === 'connection_established') {
          setConnectionId(message.connection_id || '')
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }
    
    wsRef.current.onclose = () => {
      setIsConnected(false)
      setConnectionId('')
      console.log('WebSocket disconnected')
    }
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }

  const subscribeToMarketData = () => {
    if (wsRef.current && isConnected) {
      const message = {
        type: 'subscribe_market_data',
        symbols: selectedSymbols
      }
      wsRef.current.send(JSON.stringify(message))
    }
  }

  const subscribeToAnalysisProgress = () => {
    if (wsRef.current && isConnected) {
      const message = {
        type: 'subscribe_analysis_progress',
        ticker: analysisTicket
      }
      wsRef.current.send(JSON.stringify(message))
    }
  }

  const unsubscribe = () => {
    if (wsRef.current && isConnected) {
      const message = {
        type: 'unsubscribe'
      }
      wsRef.current.send(JSON.stringify(message))
    }
  }

  const sendPing = () => {
    if (wsRef.current && isConnected) {
      const message = {
        type: 'ping'
      }
      wsRef.current.send(JSON.stringify(message))
    }
  }

  const clearMessages = () => {
    setMessages([])
  }

  useEffect(() => {
    return () => {
      disconnectWebSocket()
    }
  }, [])

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">WebSocket Real-time Streaming Test</h2>
      
      {/* Connection Controls */}
      <div className="mb-6 p-4 border rounded-lg">
        <h3 className="text-lg font-semibold mb-3">Connection</h3>
        <div className="flex items-center gap-4 mb-3">
          <button
            onClick={connectWebSocket}
            disabled={isConnected}
            className="px-4 py-2 bg-green-500 text-white rounded disabled:bg-gray-400"
          >
            Connect
          </button>
          <button
            onClick={disconnectWebSocket}
            disabled={!isConnected}
            className="px-4 py-2 bg-red-500 text-white rounded disabled:bg-gray-400"
          >
            Disconnect
          </button>
          <span className={`px-3 py-1 rounded text-sm ${
            isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        {connectionId && (
          <p className="text-sm text-gray-600">Connection ID: {connectionId}</p>
        )}
      </div>

      {/* Subscription Controls */}
      <div className="mb-6 p-4 border rounded-lg">
        <h3 className="text-lg font-semibold mb-3">Subscriptions</h3>
        
        {/* Market Data Subscription */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Market Data Symbols:</label>
          <input
            type="text"
            value={selectedSymbols.join(', ')}
            onChange={(e) => setSelectedSymbols(e.target.value.split(',').map(s => s.trim()))}
            className="w-full p-2 border rounded mb-2"
            placeholder="AAPL, GOOGL, MSFT"
          />
          <button
            onClick={subscribeToMarketData}
            disabled={!isConnected}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-400 mr-2"
          >
            Subscribe to Market Data
          </button>
        </div>

        {/* Analysis Progress Subscription */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Analysis Ticker:</label>
          <input
            type="text"
            value={analysisTicket}
            onChange={(e) => setAnalysisTicket(e.target.value)}
            className="w-full p-2 border rounded mb-2"
            placeholder="AAPL"
          />
          <button
            onClick={subscribeToAnalysisProgress}
            disabled={!isConnected}
            className="px-4 py-2 bg-purple-500 text-white rounded disabled:bg-gray-400 mr-2"
          >
            Subscribe to Analysis Progress
          </button>
        </div>

        {/* Control Buttons */}
        <div className="flex gap-2">
          <button
            onClick={unsubscribe}
            disabled={!isConnected}
            className="px-4 py-2 bg-orange-500 text-white rounded disabled:bg-gray-400"
          >
            Unsubscribe
          </button>
          <button
            onClick={sendPing}
            disabled={!isConnected}
            className="px-4 py-2 bg-gray-500 text-white rounded disabled:bg-gray-400"
          >
            Send Ping
          </button>
        </div>
      </div>

      {/* Messages Display */}
      <div className="p-4 border rounded-lg">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-semibold">Messages ({messages.length})</h3>
          <button
            onClick={clearMessages}
            className="px-3 py-1 bg-gray-500 text-white rounded text-sm"
          >
            Clear
          </button>
        </div>
        
        <div className="max-h-96 overflow-y-auto space-y-2">
          {messages.length === 0 ? (
            <p className="text-gray-500 italic">No messages yet...</p>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`p-3 rounded text-sm ${
                  message.type === 'error' ? 'bg-red-50 border-l-4 border-red-400' :
                  message.type === 'market_data' ? 'bg-blue-50 border-l-4 border-blue-400' :
                  message.type === 'analysis_progress' ? 'bg-purple-50 border-l-4 border-purple-400' :
                  'bg-gray-50 border-l-4 border-gray-400'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-medium capitalize">{message.type.replace('_', ' ')}</span>
                  {message.timestamp && (
                    <span className="text-xs text-gray-500">
                      {new Date(message.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  )}
                </div>
                {message.message && (
                  <p className="text-gray-700 mb-1">{message.message}</p>
                )}
                {message.data && (
                  <pre className="text-xs bg-white p-2 rounded overflow-x-auto">
                    {JSON.stringify(message.data, null, 2)}
                  </pre>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}