'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface HistoricalTrendsProps {
  // For now, this is a placeholder component
  // In the future, we can pass historical data from the backend
  ticker: string
}

export default function HistoricalTrends({ ticker }: HistoricalTrendsProps) {
  // Placeholder data - in the future, this will come from the backend
  // showing revenue, earnings, and FCF trends over time
  const sampleData = [
    { year: '2019', Revenue: 260, Earnings: 55, FCF: 58 },
    { year: '2020', Revenue: 274, Earnings: 57, FCF: 73 },
    { year: '2021', Revenue: 366, Earnings: 95, FCF: 93 },
    { year: '2022', Revenue: 394, Earnings: 100, FCF: 99 },
    { year: '2023', Revenue: 383, Earnings: 97, FCF: 100 },
  ]

  // For now, return null since we don't have historical data in the API response
  // This component can be enhanced later when we add historical data to the API
  return null

  // Uncomment below when historical data is available:
  /*
  return (
    <div style={{
      background: 'white',
      borderRadius: '8px',
      padding: '24px',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
      marginBottom: '20px'
    }}>
      <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px', color: '#111827' }}>
        Historical Trends
      </h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={sampleData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="Revenue" stroke="#2563eb" strokeWidth={2} />
          <Line type="monotone" dataKey="Earnings" stroke="#10b981" strokeWidth={2} />
          <Line type="monotone" dataKey="FCF" stroke="#f59e0b" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
  */
}

