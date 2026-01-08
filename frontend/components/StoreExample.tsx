'use client'

import React from 'react'
import { useAppStore } from '@/lib/store'
import { LoadingState } from './LoadingSpinner'

export function StoreExample() {
  const { 
    analyses, 
    loading, 
    error, 
    theme, 
    sidebarOpen,
    setTheme, 
    toggleSidebar, 
    clearError,
    fetchAnalysis 
  } = useAppStore()

  const handleFetchExample = () => {
    fetchAnalysis('AAPL')
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">State Management Demo</h2>
      
      <div className="space-y-4">
        {/* Theme Toggle */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium">Theme:</label>
          <button
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            className={`px-3 py-1 rounded text-sm ${
              theme === 'light' 
                ? 'bg-gray-200 text-gray-800' 
                : 'bg-gray-800 text-white'
            }`}
          >
            {theme}
          </button>
        </div>

        {/* Sidebar Toggle */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium">Sidebar:</label>
          <button
            onClick={toggleSidebar}
            className={`px-3 py-1 rounded text-sm ${
              sidebarOpen 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-200 text-gray-800'
            }`}
          >
            {sidebarOpen ? 'Open' : 'Closed'}
          </button>
        </div>

        {/* Fetch Analysis Example */}
        <div className="space-y-2">
          <button
            onClick={handleFetchExample}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            Fetch AAPL Analysis
          </button>
          
          <LoadingState loading={loading} error={error}>
            <div className="text-sm text-gray-600">
              Analyses in store: {analyses.length}
            </div>
          </LoadingState>
          
          {error && (
            <button
              onClick={clearError}
              className="text-red-600 text-sm underline"
            >
              Clear Error
            </button>
          )}
        </div>

        {/* Analyses List */}
        {analyses.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium mb-2">Stored Analyses:</h3>
            <ul className="space-y-1">
              {analyses.map((analysis) => (
                <li key={analysis.ticker} className="text-sm text-gray-600">
                  {analysis.ticker} - {analysis.recommendation}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}