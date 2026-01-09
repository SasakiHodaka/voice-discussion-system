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
  const { setSessionId, setParticipantId, sessionId, participantId } = useSessionStore()

  useEffect(() => {
    console.log('[App] Initializing...')
    console.log('[App] Browser capabilities:', {
      SpeechRecognition: !!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition,
      navigator: navigator.mediaDevices?.getUserMedia ? 'MediaDevices API available' : 'MediaDevices API not available'
    })
    
    // Auto-create session and participant on startup
    const initSession = async () => {
      if (sessionId && participantId) {
        return
      }

      try {
        // 1) create session (title as query param per API spec)
        const title = encodeURIComponent('Auto Session')
        const sessionRes = await fetch(`http://localhost:8000/api/sessions/?title=${title}`, {
          method: 'POST',
        })

        if (!sessionRes.ok) {
          console.error('[App] Failed to create session:', sessionRes.status)
          return
        }

        const sessionData = await sessionRes.json()
        const newSessionId = sessionData.session_id

        // 2) add participant
        const participantName = `User-${Date.now()}`
        const participantRes = await fetch(
          `http://localhost:8000/api/sessions/${newSessionId}/participants?name=${encodeURIComponent(participantName)}`,
          { method: 'POST' },
        )

        if (!participantRes.ok) {
          console.error('[App] Failed to add participant:', participantRes.status)
          return
        }

        const participantData = await participantRes.json()

        setSessionId(newSessionId)
        setParticipantId(participantData.participant_id)
        console.log('[App] Auto-created session & participant:', newSessionId, participantData.participant_id)
      } catch (error) {
        console.error('[App] Failed to init session/participant:', error)
      }
    }

    initSession()
    
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
                <div className="h-screen"><DiscussionViewSimplified socket={socket} /></div>
              } />
              <Route path="/discussion" element={
                <div className="h-screen"><DiscussionViewSimplified socket={socket} /></div>
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
