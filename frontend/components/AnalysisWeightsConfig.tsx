'use client'

import { useState, useEffect } from 'react'
import { AnalysisWeights } from '@/types/analysis'

export interface BusinessTypePreset {
  [key: string]: AnalysisWeights
}

interface AnalysisWeightsConfigProps {
  onWeightsChange: (weights: AnalysisWeights | null, businessType: string | null) => void
  initialBusinessType?: string
  initialWeights?: AnalysisWeights
  ticker?: string  // Ticker for auto-assign functionality
}

export default function AnalysisWeightsConfig({
  onWeightsChange,
  initialBusinessType,
  initialWeights,
  ticker
}: AnalysisWeightsConfigProps) {
  const [presets, setPresets] = useState<BusinessTypePreset>({})
  const [businessTypes, setBusinessTypes] = useState<string[]>([])
  const [selectedPreset, setSelectedPreset] = useState<string | null>(initialBusinessType || null)
  const [customWeights, setCustomWeights] = useState<AnalysisWeights>(
    initialWeights || {
      dcf_weight: 0.40,
      epv_weight: 0.40,
      asset_weight: 0.20
    }
  )
  const [useCustom, setUseCustom] = useState(!!initialWeights && !initialBusinessType)
  const [loading, setLoading] = useState(true)
  const [autoAssigning, setAutoAssigning] = useState(false)

  useEffect(() => {
    fetchPresets()
  }, [])

  useEffect(() => {
    if (useCustom) {
      onWeightsChange(customWeights, null)
    } else if (selectedPreset && presets[selectedPreset]) {
      onWeightsChange(presets[selectedPreset], selectedPreset)
    }
  }, [selectedPreset, customWeights, useCustom, presets])

  const fetchPresets = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/analysis-presets`)
      const data = await response.json()
      setPresets(data.presets)
      setBusinessTypes(data.business_types)
      
      if (!selectedPreset && data.business_types.length > 0) {
        setSelectedPreset('default')
      }
    } catch (error) {
      console.error('Error fetching presets:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset)
    setUseCustom(false)
  }

  const handleCustomToggle = () => {
    setUseCustom(!useCustom)
    if (!useCustom) {
      // When switching to custom, use current preset weights as starting point
      if (selectedPreset && presets[selectedPreset]) {
        setCustomWeights(presets[selectedPreset])
      }
    }
  }

  const handleWeightChange = (field: keyof AnalysisWeights, value: number) => {
    setCustomWeights(prev => ({
      ...prev,
      [field]: Math.max(0, Math.min(1, value))
    }))
  }

  const normalizeWeights = (weights: AnalysisWeights) => {
    const total = weights.dcf_weight + weights.epv_weight + weights.asset_weight
    if (total > 0) {
      return {
        ...weights,
        dcf_weight: weights.dcf_weight / total,
        epv_weight: weights.epv_weight / total,
        asset_weight: weights.asset_weight / total
      }
    }
    return weights
  }

  const handleNormalize = () => {
    setCustomWeights(prev => normalizeWeights(prev))
  }

  const handleAutoAssign = async () => {
    if (!ticker) {
      alert('Ticker is required for auto-assignment')
      return
    }
    
    setAutoAssigning(true)
    try {
      const { stockApi } = await import('@/lib/api')
      const result = await stockApi.autoAssignBusinessType(ticker)
      setSelectedPreset(result.detected_business_type)
      setCustomWeights(result.weights)
      setUseCustom(false)
      onWeightsChange(result.weights, result.detected_business_type)
      alert(`Auto-assigned: ${result.business_type_display}`)
    } catch (error: any) {
      console.error('Error auto-assigning business type:', error)
      alert(`Error: ${error.message || 'Failed to auto-assign business type'}`)
    } finally {
      setAutoAssigning(false)
    }
  }

  if (loading) {
    return <div className="text-sm text-gray-500">Loading presets...</div>
  }

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-white">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Analysis Configuration</h3>
        {ticker && (
          <button
            onClick={handleAutoAssign}
            disabled={autoAssigning}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            title="Use AI to automatically detect the best business type for this company"
          >
            {autoAssigning ? '🔄 Detecting...' : '🤖 Auto-Assign'}
          </button>
        )}
      </div>
      
      {ticker && (
        <div className="text-xs text-gray-500 italic mb-2">
          💡 Tip: Click "Auto-Assign" to use AI (AWS Bedrock/OpenAI) to automatically detect the best valuation model based on company research
        </div>
      )}
      
      {/* Preset Selection */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">Business Type Preset</label>
        <div className="flex items-center space-x-2">
          <input
            type="radio"
            id="use-preset"
            checked={!useCustom}
            onChange={handleCustomToggle}
            className="mr-2"
          />
          <label htmlFor="use-preset" className="text-sm">Use Preset</label>
        </div>
        
        {!useCustom && (
          <>
            <select
              value={selectedPreset || ''}
              onChange={(e) => handlePresetChange(e.target.value)}
              className="w-full p-2 border rounded text-sm"
            >
              {businessTypes.map(bt => (
                <option key={bt} value={bt}>
                  {bt.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
            
            {/* Display weights for selected preset */}
            {selectedPreset && presets[selectedPreset] && (
              <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
                <h4 className="text-sm font-semibold mb-2 text-gray-700">Analysis Weighting</h4>
                
                {/* Valuation Weights */}
                <div className="mb-3">
                  <p className="text-xs font-medium text-gray-600 mb-1">Valuation Weights:</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-600">DCF:</span>
                      <span className="font-medium">{(presets[selectedPreset].dcf_weight * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">EPV:</span>
                      <span className="font-medium">{(presets[selectedPreset].epv_weight * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Asset-Based:</span>
                      <span className="font-medium">{(presets[selectedPreset].asset_weight * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
                
              </div>
            )}
          </>
        )}
      </div>

      {/* Custom Weights Toggle */}
      <div className="flex items-center space-x-2">
        <input
          type="radio"
          id="use-custom"
          checked={useCustom}
          onChange={handleCustomToggle}
          className="mr-2"
        />
        <label htmlFor="use-custom" className="text-sm font-medium">Manual Configuration</label>
      </div>

      {/* Custom Weights Configuration */}
      {useCustom && (
        <div className="space-y-4 border-t pt-4">
          <div>
            <h4 className="text-sm font-semibold mb-2">Valuation Weights (must sum to 1.0)</h4>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <label className="w-32 text-sm">DCF:</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={customWeights.dcf_weight.toFixed(2)}
                  onChange={(e) => handleWeightChange('dcf_weight', parseFloat(e.target.value) || 0)}
                  className="flex-1 p-1 border rounded text-sm"
                />
                <span className="text-xs text-gray-500">{(customWeights.dcf_weight * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center space-x-2">
                <label className="w-32 text-sm">EPV:</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={customWeights.epv_weight.toFixed(2)}
                  onChange={(e) => handleWeightChange('epv_weight', parseFloat(e.target.value) || 0)}
                  className="flex-1 p-1 border rounded text-sm"
                />
                <span className="text-xs text-gray-500">{(customWeights.epv_weight * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center space-x-2">
                <label className="w-32 text-sm">Asset-Based:</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={customWeights.asset_weight.toFixed(2)}
                  onChange={(e) => handleWeightChange('asset_weight', parseFloat(e.target.value) || 0)}
                  className="flex-1 p-1 border rounded text-sm"
                />
                <span className="text-xs text-gray-500">{(customWeights.asset_weight * 100).toFixed(0)}%</span>
              </div>
              <div className="text-xs text-gray-500">
                Total: {((customWeights.dcf_weight + customWeights.epv_weight + customWeights.asset_weight) * 100).toFixed(1)}%
                {Math.abs(customWeights.dcf_weight + customWeights.epv_weight + customWeights.asset_weight - 1.0) > 0.01 && (
                  <span className="text-red-500 ml-2">⚠ Should sum to 100%</span>
                )}
              </div>
              <button
                onClick={handleNormalize}
                className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
              >
                Normalize Valuation Weights
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

