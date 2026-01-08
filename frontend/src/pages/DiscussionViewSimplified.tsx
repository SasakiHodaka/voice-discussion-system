import React, { useState, useEffect, useCallback } from 'react'
import { Socket } from 'socket.io-client'
import { useSessionStore } from '@/lib/store'
import { sessionAPI, analysisAPI } from '@/lib/api'
import { MessageCircle, Mic, MicOff } from 'lucide-react'
import { createSpeechRecognizer } from '@/lib/speech'

interface DiscussionViewProps {
  socket: Socket | null
}

type Tab = 'chat' | 'whiteboard' | 'analysis'

const DiscussionViewSimplified: React.FC<DiscussionViewProps> = ({ socket }) => {
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [messages, setMessages] = useState<any[]>([])
  const [listening, setListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [speech, setSpeech] = useState<ReturnType<typeof createSpeechRecognizer> | null>(null)
  const [speakerMap, setSpeakerMap] = useState<Map<string, string>>(new Map())
  const [textInput, setTextInput] = useState('')
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [editTarget, setEditTarget] = useState<string>('')
  const [aliasInput, setAliasInput] = useState<string>('')

  const {
    sessionId,
    participantId,
    sessionTitle,
    participants,
    segments,
    addSegment,
  } = useSessionStore()

  // Helpers should be declared before use in effects to avoid TDZ
  const nameById = useCallback((id: string): string | null => {
    const p = participants.find((x: any) => x.participant_id === id)
    return p?.name || null
  }, [participants])

  const speakerLabel = useCallback((pid?: string): string => {
    if (!pid) return 'Unknown'
    return speakerMap.get(pid) || nameById(pid) || pid
  }, [speakerMap, nameById])

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) {
      console.log('[DiscussionView] Empty text')
      return
    }
    if (!socket) {
      console.log('[DiscussionView] No socket')
      return
    }
    if (!sessionId) {
      console.log('[DiscussionView] No sessionId')
      return
    }
    if (!participantId) {
      console.log('[DiscussionView] No participantId')
      return
    }

    const msg = {
      session_id: sessionId,
      participant_id: participantId,
      speaker: speakerLabel(participantId),
      text: text.trim(),
      timestamp: new Date().toISOString(),
    }

    console.log('[DiscussionView] Sending message:', msg)
    socket.emit('send_text', msg)
    setTextInput('')
    setInterimText('')
  }, [socket, sessionId, participantId, speakerLabel])

  // Initialize speech recognition
  useEffect(() => {
    const browserSpeech = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    setSpeechSupported(!!browserSpeech)

    if (browserSpeech) {
      const s = createSpeechRecognizer({
        continuous: true,
        interimResults: true,
        language: 'ja-JP',
        onResult: (text: string, isFinal: boolean) => {
          console.log('[SpeechRecognizer] onResult:', text, 'isFinal:', isFinal)
          if (isFinal) {
            console.log('[SpeechRecognizer] Calling sendMessage with:', text)
            sendMessage(text)
          } else {
            setInterimText(text)
          }
        },
        onError: (error: string) => {
          console.error('[SpeechRecognizer] Error:', error)
          setListening(false)
        }
      })
      setSpeech(s)
    }
  }, [sendMessage])

  // Setup socket listeners
  useEffect(() => {
    if (!socket) return

    if (sessionId) {
      socket.emit('join', {
        session_id: sessionId,
        participant_name: participantId || 'Anonymous',
        role: 'participant',
      })
    }

    socket.on('text_received', (data) => {
      const speaker = data.speaker || nameById(data.participant_id) || 'Unknown'
      setMessages((prev) => [...prev, { ...data, speaker }])
    })

    // Backward compatibility: different server event names
    socket.on('analysis_result', (data) => {
      setAnalysisData(data)
      addSegment(data)
    })
    socket.on('segment_analyzed', (data) => {
      // shape: { session_id, segment_id, result }
      setAnalysisData(data.result)
      addSegment(data.result)
    })
    socket.on('segment_analyzed_integrated', (data) => {
      // shape: { session_id, segment_id, result }
      setAnalysisData(data.result)
      if (data.result?.base_analysis) {
        addSegment(data.result.base_analysis)
      }
    })

    return () => {
      socket.off('text_received')
      socket.off('analysis_result')
      socket.off('segment_analyzed')
      socket.off('segment_analyzed_integrated')
    }
  }, [socket, sessionId, participantId, nameById, addSegment])

  // Keep speaker labels aligned with participants
  useEffect(() => {
    setSpeakerMap((prev) => {
      const next = new Map(prev)
      participants.forEach((p: any) => {
        if (!next.has(p.participant_id)) {
          next.set(p.participant_id, p.name || `話者${next.size + 1}`)
        }
      })
      return next
    })
  }, [participants])

  // Initialize editTarget
  useEffect(() => {
    if (!editTarget && participants.length > 0) {
      const firstId = participants[0].participant_id
      setEditTarget(firstId)
      setAliasInput(speakerLabel(firstId))
    } else if (editTarget) {
      setAliasInput(speakerLabel(editTarget))
    }
  }, [participants, editTarget, speakerMap])

  // nameById, speakerLabel are defined above with useCallback

  const handleUpdateAlias = (targetId: string, newAlias: string) => {
    if (!newAlias.trim()) return
    setSpeakerMap(new Map(speakerMap).set(targetId, newAlias.trim()))
    setAliasInput(newAlias.trim())
  }

  // Voice input
  const startListening = () => {
    if (!speech) return
    setListening(true)
    setInterimText('')
    speech.start()
    speech.onresult = (e: any) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const transcript = e.results[i][0].transcript
        if (e.results[i].isFinal) {
          sendMessage(transcript)
        } else {
          interim += transcript
        }
      }
      setInterimText(interim)
    }
    speech.onend = () => {
      setListening(false)
    }
  }

  const stopListening = () => {
    if (speech) {
      speech.stop()
      setListening(false)
    }
  }

  // sendMessage is defined above with useCallback

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">{sessionTitle || 'Discussion'}</h1>
        <p className="text-sm text-gray-600">Participants: {participants.map((p: any) => p.name).join(', ')}</p>
      </div>

      {/* Input Section */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex gap-2">
          {speechSupported && (
            <button
              onClick={listening ? stopListening : startListening}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                listening
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {listening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
          )}
          <input
            type="text"
            placeholder={interimText || '会話を入力...'}
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage(textInput)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
          <button
            onClick={() => sendMessage(textInput)}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
          >
            送信
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-2 font-medium border-b-2 transition ${
              activeTab === 'chat'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <MessageCircle className="inline mr-2 w-4 h-4" />
            会話
          </button>
          <button
            onClick={() => setActiveTab('whiteboard')}
            className={`px-4 py-2 font-medium border-b-2 transition ${
              activeTab === 'whiteboard'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            ホワイトボード
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={`px-4 py-2 font-medium border-b-2 transition ${
              activeTab === 'analysis'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            解析
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="h-full flex flex-col">
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((msg, idx) => (
                <div key={idx} className="flex gap-3">
                  <div className="w-24 text-sm font-semibold text-gray-700 flex-shrink-0">
                    {msg.speaker}
                  </div>
                  <div className="flex-1">
                    <p className="text-gray-900">{msg.text}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(msg.timestamp).toLocaleTimeString('ja-JP')}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-200 bg-white p-6">
              <div className="flex gap-2">
                <button
                  onClick={() => sendMessage(textInput)}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
                  style={{ display: 'none' }}
                >
                  送信
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Whiteboard Tab */}
        {activeTab === 'whiteboard' && (
          <div className="h-full overflow-y-auto p-6">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl font-bold mb-6 text-gray-900">会話要約</h2>

              {messages.length === 0 ? (
                <p className="text-gray-500 text-center py-8">会話がまだありません</p>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg, idx) => (
                    <div key={idx} className="bg-white rounded-lg p-4 border border-gray-200">
                      <div className="flex items-start gap-4">
                        <div className="bg-blue-100 text-blue-700 font-semibold px-3 py-1 rounded text-sm w-24 text-center flex-shrink-0">
                          {msg.speaker}
                        </div>
                        <div className="flex-1">
                          <p className="text-gray-900 leading-relaxed">{msg.text}</p>
                          <p className="text-xs text-gray-500 mt-2">
                            {new Date(msg.timestamp).toLocaleTimeString('ja-JP')}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Analysis Tab */}
        {activeTab === 'analysis' && (
          <div className="h-full overflow-y-auto p-6">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl font-bold mb-6 text-gray-900">解析結果</h2>

              {!analysisData ? (
                <p className="text-gray-500 text-center py-8">
                  セグメントを解析してください
                </p>
              ) : (
                <div className="space-y-6">
                  {/* Health Score */}
                  <div className="bg-white rounded-lg p-6 border border-gray-200">
                    <h3 className="text-lg font-semibold mb-4 text-gray-900">議論の健全性</h3>
                    <div className="flex items-end gap-4">
                      <div className="flex-1">
                        <div className="w-full bg-gray-200 rounded-full h-4">
                          <div
                            className={`h-4 rounded-full transition ${
                              (analysisData.summary?.discussion_health || 0) > 0.7
                                ? 'bg-green-600'
                                : (analysisData.summary?.discussion_health || 0) > 0.5
                                ? 'bg-yellow-600'
                                : 'bg-red-600'
                            }`}
                            style={{
                              width: `${(analysisData.summary?.discussion_health || 0) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                      <span className="text-2xl font-bold text-gray-900">
                        {Math.round((analysisData.summary?.discussion_health || 0) * 100)}%
                      </span>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <p className="text-sm text-gray-600 mb-1">混乱度</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {Math.round((analysisData.summary?.key_metrics?.confusion || 0) * 100)}%
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <p className="text-sm text-gray-600 mb-1">停滞度</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {Math.round((analysisData.summary?.key_metrics?.stagnation || 0) * 100)}%
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <p className="text-sm text-gray-600 mb-1">理解度</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {Math.round((analysisData.summary?.key_metrics?.understanding || 0) * 100)}%
                      </p>
                    </div>
                  </div>

                  {/* Cognitive Stats */}
                  <div className="bg-white rounded-lg p-6 border border-gray-200">
                    <h3 className="text-lg font-semibold mb-4 text-gray-900">参加者の認知状態</h3>
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm text-gray-600 mb-1">平均理解度</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded h-2">
                            <div
                              className="bg-blue-600 h-2 rounded"
                              style={{
                                width: `${(analysisData.summary?.cognitive_stats?.avg_understanding || 0) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-sm font-semibold text-gray-700 w-12">
                            {Math.round((analysisData.summary?.cognitive_stats?.avg_understanding || 0) * 100)}%
                          </span>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 mb-1">平均自信度</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded h-2">
                            <div
                              className="bg-green-600 h-2 rounded"
                              style={{
                                width: `${(analysisData.summary?.cognitive_stats?.avg_confidence || 0) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-sm font-semibold text-gray-700 w-12">
                            {Math.round((analysisData.summary?.cognitive_stats?.avg_confidence || 0) * 100)}%
                          </span>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 mb-1">平均躊躇度</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded h-2">
                            <div
                              className="bg-red-600 h-2 rounded"
                              style={{
                                width: `${(analysisData.summary?.cognitive_stats?.avg_hesitation || 0) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-sm font-semibold text-gray-700 w-12">
                            {Math.round((analysisData.summary?.cognitive_stats?.avg_hesitation || 0) * 100)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Intervention */}
                  {analysisData.intervention?.needed && (
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-6">
                      <h3 className="text-lg font-semibold mb-2 text-orange-900">推奨アクション</h3>
                      <p className="text-orange-800 mb-2">{analysisData.intervention?.message}</p>
                      <p className="text-sm text-orange-700">
                        優先度: <span className="font-semibold">{analysisData.intervention?.priority}</span>
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default DiscussionViewSimplified
