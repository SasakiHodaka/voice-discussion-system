import React, { useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import { useSessionStore } from './lib/store'
import SessionDashboard from './pages/SessionDashboard'
import DiscussionView from './pages/DiscussionView'
import './index.css'

interface AppProps {}

const App: React.FC<AppProps> = () => {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const { sessionId, participantId } = useSessionStore()

  useEffect(() => {
    // Initialize socket connection
    const socketInstance = io('http://localhost:8000', {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
    })

    socketInstance.on('connect', () => {
      console.log('Connected to server')
      setIsConnected(true)
    })

    socketInstance.on('disconnect', () => {
      console.log('Disconnected from server')
      setIsConnected(false)
    })

    socketInstance.on('error', (error) => {
      console.error('Socket error:', error)
    })

    setSocket(socketInstance)

    return () => {
      socketInstance.close()
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="container py-4">
          <h1 className="text-2xl font-bold">音声議論システム</h1>
          <p className="text-gray-600">AI分析による議論支援</p>
        </div>
      </header>

      <main className="container py-8">
        {isConnected ? (
          <>
            {sessionId && participantId ? (
              <DiscussionView socket={socket} />
            ) : (
              <SessionDashboard socket={socket} />
            )}
          </>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-800">
              Connecting to server...
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
