import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { io, Socket } from 'socket.io-client'
import { useSessionStore } from './lib/store'
import SessionDashboard from './pages/SessionDashboard'
import DiscussionViewSimplified from './pages/DiscussionViewSimplified'
import './index.css'

interface AppProps {}

const App: React.FC<AppProps> = () => {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const { sessionId, participantId } = useSessionStore()

  useEffect(() => {
    console.log('[App] Initializing...')
    console.log('[App] Browser capabilities:', {
      SpeechRecognition: !!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition,
      navigator: navigator.mediaDevices?.getUserMedia ? 'MediaDevices API available' : 'MediaDevices API not available'
    })
    
    // Initialize socket connection
    const socketInstance = io('http://localhost:8000', {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
    })

    socketInstance.on('connect', () => {
      console.log('[App] Connected to server')
      setIsConnected(true)
    })

    socketInstance.on('disconnect', () => {
      console.log('[App] Disconnected from server')
      setIsConnected(false)
    })

    socketInstance.on('error', (error) => {
      console.error('[App] Socket error:', error)
    })

    setSocket(socketInstance)

    return () => {
      socketInstance.close()
    }
  }, [])

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="container py-4">
            <h1 className="text-2xl font-bold">音声議論システム</h1>
            <p className="text-gray-600">AI分析による議論支援</p>
          </div>
        </header>

        <main className="py-8">
          {isConnected ? (
            <Routes>
              <Route path="/" element={
                sessionId && participantId ? (
                  <Navigate to="/discussion" replace />
                ) : (
                  <div className="container"><SessionDashboard socket={socket} /></div>
                )
              } />
              <Route path="/dashboard" element={<div className="container"><SessionDashboard socket={socket} /></div>} />
              <Route path="/discussion" element={
                sessionId && participantId ? (
                  <div className="h-screen"><DiscussionViewSimplified socket={socket} /></div>
                ) : (
                  <Navigate to="/dashboard" replace />
                )
              } />
            </Routes>
          ) : (
            <div className="container">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-yellow-800">
                  Connecting to server...
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
