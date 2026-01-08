import WebSocketTest from '@/components/WebSocketTest'

export default function WebSocketTestPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <WebSocketTest />
    </div>
  )
}

export const metadata = {
  title: 'WebSocket Test - Stock Analysis Tool',
  description: 'Test real-time WebSocket streaming functionality',
}