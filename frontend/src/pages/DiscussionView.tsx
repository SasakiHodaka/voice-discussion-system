import React, { useState, useEffect } from 'react'
import { Socket } from 'socket.io-client'
import { useSessionStore } from '@/lib/store'
import { sessionAPI, analysisAPI } from '@/lib/api'
import { MessageCircle, BarChart3, Mic, MicOff, Activity } from 'lucide-react'
import { createSpeechRecognizer } from '@/lib/speech'
import AnalysisDashboard from '@/components/AnalysisDashboard'

interface DiscussionViewProps {
  socket: Socket | null
}

const DiscussionView: React.FC<DiscussionViewProps> = ({ socket }) => {
  const [messages, setMessages] = useState<any[]>([])
  const [listening, setListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [speech, setSpeech] = useState<ReturnType<typeof createSpeechRecognizer> | null>(null)
  const [speakerMap, setSpeakerMap] = useState<Map<string, string>>(new Map())
  const [fullAnalysis, setFullAnalysis] = useState<any>(null)
  const [showDashboard, setShowDashboard] = useState(false)
  const [speechError, setSpeechError] = useState<string | null>(null)

  const {
    sessionId,
    participantId,
    sessionTitle,
    participants,
    addParticipant,
    removeParticipant,
  } = useSessionStore()

  // Auto-assign speakers based on participantId
  const getOrAssignSpeaker = (pid: string): string => {
    if (speakerMap.has(pid)) {
      return speakerMap.get(pid)!
    }
    const newSpeaker = `話者${speakerMap.size + 1}`
    setSpeakerMap(new Map(speakerMap).set(pid, newSpeaker))
    return newSpeaker
  }

  useEffect(() => {
    if (!socket) return

    // ensure we are in the room (handles page reload while connected)
    if (sessionId) {
      socket.emit('join', {
        session_id: sessionId,
        participant_name: participantId || 'Anonymous',
        role: 'participant',
      })
    }

    socket.on('text_received', (data) => {
      // Auto-assign speaker if not present
      if (!data.speaker && data.participant_id) {
        data.speaker = getOrAssignSpeaker(data.participant_id)
      }
      setMessages((prev) => [...prev, data])
    })
    socket.on('participant_joined', (data) => addParticipant(data.participant))
    socket.on('participant_left', (data) => removeParticipant(data.participant_id))

    return () => {
      socket.off('text_received')
      socket.off('participant_joined')
      socket.off('participant_left')
    }
  }, [socket, sessionId, participantId, addParticipant, removeParticipant])

  // setup speech recognizer (音声のみ運用: 確定結果で自動送信)
  useEffect(() => {
    console.log('[DiscussionView] Setting up speech recognizer...')
    const s = createSpeechRecognizer({
      onResult: (text, isFinal) => {
        console.log('[DiscussionView] onResult:', { text, isFinal })
        if (isFinal) {
          const t = (text || '').trim()
          if (t) {
            sendRecognizedText(t)
          }
          setInterimText('')
        } else {
          setInterimText(text)
        }
      },
      onError: (error) => {
        console.error('[DiscussionView] onError:', error)
        setSpeechError(error)
        setListening(false)
      }
    })
    console.log('[DiscussionView] Speech recognizer created, supported:', s.supported)
    setSpeechSupported(s.supported)
    setSpeech(s)
    return () => {
      console.log('[DiscussionView] Cleaning up speech recognizer')
      s.dispose()
    }
  }, [])

  // PTT: Spaceキーで録音開始/停止
  useEffect(() => {
    const downHandler = (e: KeyboardEvent) => {
      if (e.code !== 'Space') return
      console.log('[DiscussionView] Space key down, speechSupported:', speechSupported, 'speech:', !!speech, 'listening:', listening)
      if (!speechSupported || !speech) return
      if (listening) return
      e.preventDefault()
      console.log('[DiscussionView] Starting speech recognition via Space key')
      speech.start()
      setListening(true)
    }
    const upHandler = (e: KeyboardEvent) => {
      if (e.code !== 'Space') return
      console.log('[DiscussionView] Space key up, listening:', listening)
      if (!speechSupported || !speech) return
      if (!listening) return
      e.preventDefault()
      console.log('[DiscussionView] Stopping speech recognition via Space key')
      speech.stop()
      setListening(false)
    }
    window.addEventListener('keydown', downHandler)
    window.addEventListener('keyup', upHandler)
    return () => {
      window.removeEventListener('keydown', downHandler)
      window.removeEventListener('keyup', upHandler)
    }
  }, [speechSupported, speech, listening])

  const sendRecognizedText = (content: string) => {
    if (!content.trim()) return
    if (!sessionId || !participantId) {
      console.warn('Missing sessionId or participantId; cannot send')
      return
    }
    const autoSpeaker = getOrAssignSpeaker(participantId)
    const now = new Date().toISOString()
    setMessages((prev) => [
      ...prev,
      {
        session_id: sessionId,
        participant_id: participantId,
        participant_name: nameById(participantId),
        speaker: autoSpeaker,
        text: content,
        timestamp: now,
      },
    ])
    socket?.emit('send_text', {
      session_id: sessionId,
      participant_id: participantId,
      speaker: autoSpeaker,
      text: content,
    })
  }

  const handleFullAnalysis = async () => {
    if (!sessionId) return
    setShowDashboard(true)

    const utterances = messages.map((m, idx) => ({
      utterance_id: `u${idx}`,
      start: idx * 2,
      end: idx * 2 + 1.5,
      speaker: m.speaker || m.participant_name || nameById(m.participant_id) || 'Unknown',
      text: m.text || '',
    }))

    try {
      const result = await analysisAPI.analyzeFull({
        session_id: sessionId,
        utterances,
      })
      setFullAnalysis(result)
    } catch (e) {
      console.error('Full analysis failed:', e)
    }
  }

  const nameById = (id: string) => {
    const found = participants.find((p: any) => p.participant_id === id)
    return found?.name || id
  }

  return (
    <div className="space-y-6 notranslate" translate="no">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-2">{sessionTitle}</h2>
        <div className="flex flex-wrap gap-2">
          {participants.map((p: any) => (
            <span key={p.participant_id} className="participant-badge">
              {p.name}
            </span>
          ))}
        </div>
      </div>

      {/* Messages and Input */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <MessageCircle size={20} />
          ディスカッション
        </h3>

        <div className="space-y-3 max-h-96 overflow-y-auto mb-4">
          {messages.map((msg, idx) => {
            const mine = msg.participant_id === participantId
            return (
              <div key={idx} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded p-3 shadow-sm ${mine ? 'bg-blue-600 text-white' : 'bg-gray-50 text-gray-900'}`}>
                  <p className={`text-xs ${mine ? 'text-blue-100' : 'text-gray-600'} mb-1`}>
                    {msg.speaker ? `${msg.speaker}（${msg.participant_name || nameById(msg.participant_id)}）` : (msg.participant_name || nameById(msg.participant_id))}
                  </p>
                  <p translate="no">{msg.text}</p>
                  <p className={`text-[10px] mt-1 ${mine ? 'text-blue-100/80' : 'text-gray-500'}`}>
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        <div className="flex items-center gap-3 mb-4">
          {speechSupported ? (
            <button
              aria-label={listening ? '音声入力停止' : '音声入力開始'}
              title="スペース長押しで話す（PTT） / クリックでトグル"
              onClick={() => {
                console.log('[DiscussionView] Mic button clicked, listening:', listening)
                if (!speech) {
                  console.log('[DiscussionView] No speech recognizer available')
                  return
                }
                if (listening) {
                  console.log('[DiscussionView] Stopping via button click')
                  speech.stop()
                  setListening(false)
                } else {
                  console.log('[DiscussionView] Starting via button click')
                  speech.start()
                  setListening(true)
                }
              }}
              className={`px-4 py-3 rounded-xl border text-base flex items-center gap-2 ${listening ? 'bg-red-50 border-red-300 text-red-700' : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}`}
            >
              {listening ? <MicOff size={18} /> : <Mic size={18} />}
              {listening ? '録音中…' : '音声入力'}
            </button>
          ) : (
            <p className="text-sm text-gray-500">このブラウザは音声入力に未対応です</p>
          )}
          {speechError && (
            <p className="text-sm text-red-500">音声エラー: {speechError}</p>
          )}
          {interimText && (
            <p className="text-sm text-gray-600 truncate ml-auto">{interimText}</p>
          )}
        </div>

        <button
          onClick={handleFullAnalysis}
          disabled={messages.length === 0}
          className="w-full bg-purple-600 text-white px-4 py-3 rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <Activity size={18} />
          全体分析を実行
        </button>
      </div>

      {/* Full Analysis Dashboard */}
      {showDashboard && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">全体分析ダッシュボード</h2>
            <button
              onClick={() => setShowDashboard(false)}
              className="text-sm text-gray-600 hover:text-gray-800 px-3 py-1 border rounded-lg"
            >
              閉じる
            </button>
          </div>
          <AnalysisDashboard analysis={fullAnalysis} />
        </div>
      )}
    </div>
  )
}

export default DiscussionView
