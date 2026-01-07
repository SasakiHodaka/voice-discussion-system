import React, { useState, useEffect } from 'react'
import { Socket } from 'socket.io-client'
import { sessionAPI } from '@/lib/api'
import { useSessionStore } from '@/lib/store'
import { Plus } from 'lucide-react'

interface SessionDashboardProps {
  socket: Socket | null
}

const SessionDashboard: React.FC<SessionDashboardProps> = ({ socket }) => {
  const [sessions, setSessions] = useState<any[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [newSessionTitle, setNewSessionTitle] = useState('')
  const [newSessionDesc, setNewSessionDesc] = useState('')
  const [participantName, setParticipantName] = useState('')
  const [selectedSession, setSelectedSession] = useState<any | null>(null)

  const { setSession, setParticipant, addParticipant } = useSessionStore()

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      const data = await sessionAPI.listSessions()
      setSessions(data)
    } catch (error) {
      console.error('Error loading sessions:', error)
    }
  }

  const handleCreateSession = async () => {
    if (!newSessionTitle.trim() || !participantName.trim()) return

    try {
      const session = await sessionAPI.createSession({
        title: newSessionTitle,
        description: newSessionDesc,
        creator_name: participantName,
      })

      setSession(session.session_id, session.title)
      setParticipant(session.participants[0].participant_id, participantName)
      // keep local participant list in sync
      session.participants.forEach((p: any) => addParticipant(p))

      // join Socket.IO room so we receive broadcasts
      socket?.emit('join', {
        session_id: session.session_id,
        participant_name: participantName,
        role: 'participant',
      })

      setNewSessionTitle('')
      setNewSessionDesc('')
      setParticipantName('')
      setIsCreating(false)
    } catch (error) {
      console.error('Error creating session:', error)
    }
  }

  const handleJoinSession = async (session: any) => {
    if (!participantName.trim()) return

    try {
      const participant = await sessionAPI.addParticipant(session.session_id, {
        name: participantName,
      })

      setSession(session.session_id, session.title)
      setParticipant(participant.participant_id, participantName)
      addParticipant({ participant_id: participant.participant_id, name: participantName })

      socket?.emit('join', {
        session_id: session.session_id,
        participant_name: participantName,
        role: 'participant',
      })

      setParticipantName('')
      setSelectedSession(null)
    } catch (error) {
      console.error('Error joining session:', error)
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-4">ディスカッション・セッション</h2>

        {!isCreating ? (
          <button
            onClick={() => setIsCreating(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700"
          >
            <Plus size={20} />
            新規セッション
          </button>
        ) : (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-xl font-bold mb-4">新規セッションを作成</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">セッションタイトル</label>
                <input
                  type="text"
                  value={newSessionTitle}
                  onChange={(e) => setNewSessionTitle(e.target.value)}
                  placeholder="セッションタイトルを入力"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">説明（任意）</label>
                <textarea
                  value={newSessionDesc}
                  onChange={(e) => setNewSessionDesc(e.target.value)}
                  placeholder="任意の説明"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">チーム名</label>
                <input
                  type="text"
                  value={participantName}
                  onChange={(e) => setParticipantName(e.target.value)}
                  placeholder="チーム名を入力"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleCreateSession}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
                >
                  Create
                </button>
                <button
                  onClick={() => setIsCreating(false)}
                  className="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-2xl font-bold mb-4">Active Sessions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sessions.map((session) => (
            <div key={session.session_id} className="bg-white rounded-lg shadow p-4">
              <h4 className="text-lg font-bold mb-2">{session.title}</h4>
              <p className="text-gray-600 text-sm mb-3">{session.description}</p>
              <div className="mb-3">
                <p className="text-xs text-gray-500">
                  Teams: {session.participants.length}
                </p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {session.participants.slice(0, 3).map((p: any) => (
                    <span
                      key={p.participant_id}
                      className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded"
                    >
                      {p.name}
                    </span>
                  ))}
                </div>
              </div>
              {!selectedSession || selectedSession.session_id !== session.session_id ? (
                <button
                  onClick={() => setSelectedSession(session)}
                  className="w-full bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 text-sm"
                >
                  Join Session
                </button>
              ) : (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={participantName}
                    onChange={(e) => setParticipantName(e.target.value)}
                    placeholder="チーム名を入力"
                    className="w-full px-2 py-1 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => handleJoinSession(session)}
                    className="w-full bg-green-600 text-white px-3 py-2 rounded-lg hover:bg-green-700 text-sm"
                  >
                    Confirm Join
                  </button>
                  <button
                    onClick={() => setSelectedSession(null)}
                    className="w-full bg-gray-300 text-gray-700 px-3 py-2 rounded-lg text-sm"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default SessionDashboard
