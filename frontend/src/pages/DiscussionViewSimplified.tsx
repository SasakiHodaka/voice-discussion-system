import React, { useState, useEffect, useCallback } from 'react'
import { Socket } from 'socket.io-client'
import { useSessionStore } from '@/lib/store'
import { sessionAPI, analysisAPI } from '@/lib/api'
import { MessageCircle, Mic, MicOff } from 'lucide-react'
import { createSpeechRecognizer } from '@/lib/speech'
import TopicMapEditor from '@/components/TopicMapEditor'

interface DiscussionViewProps {
  socket: Socket | null
}

type Tab = 'chat' | 'analysis' | 'topicmap'

// 音声入力の自動送信を有効化
const AUTO_SEND_SPEECH = true

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
  const [analyzing, setAnalyzing] = useState(false)
  const [editTarget, setEditTarget] = useState<string>('')
  const [aliasInput, setAliasInput] = useState<string>('')
  const [suggestedTerms, setSuggestedTerms] = useState<any[]>([])
  const [loadingTerms, setLoadingTerms] = useState(false)

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

  const runAnalysis = useCallback(() => {
    if (!socket || !sessionId) {
      console.log('[DiscussionView] Cannot analyze: no socket or session')
      return
    }

    setAnalyzing(true)

    // Convert messages to utterances format (compatible with backend)
    const utterances = messages.map((msg, idx) => ({
      utterance_id: `u${idx}`,
      speaker: msg.speaker || 'Unknown',
      text: msg.text,
      start: idx * 2,  // Simple time assignment (2 seconds per message)
      end: idx * 2 + 2,
      audio_stats: null
    }))

    const analysisPayload = {
      session_id: sessionId,
      segment_id: segments.length,
      start_sec: 0,
      end_sec: messages.length * 2,
      utterances
    }

    console.log('[DiscussionView] Triggering analysis:', analysisPayload)
    socket.emit('analyze_segment_integrated', analysisPayload)
  }, [socket, sessionId, messages, segments])

  const loadSuggestedTerms = useCallback(async () => {
    if (!sessionId || messages.length === 0) {
      return
    }

    setLoadingTerms(true)
    try {
      const response = await fetch('http://127.0.0.1:8000/api/terms/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          messages: messages,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setSuggestedTerms(data.terms || [])
      }
    } catch (error) {
      console.error('[DiscussionView] Error loading terms:', error)
    } finally {
      setLoadingTerms(false)
    }
  }, [sessionId, messages])

  // Initialize speech recognition
  useEffect(() => {
    const browserSpeech = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    setSpeechSupported(!!browserSpeech)

    if (!browserSpeech) return

    const s = createSpeechRecognizer({
      continuous: true,
      interimResults: true,
      language: 'ja-JP',
      onResult: (text: string, isFinal: boolean) => {
        console.log('[SpeechRecognizer] onResult:', text, 'isFinal:', isFinal)
        if (isFinal) {
          console.log('[SpeechRecognizer] Final text received:', text)
          setInterimText('')
          setTextInput(text)

          // Auto-send can be re-enabled via flag above
          if (
            AUTO_SEND_SPEECH &&
            text.trim() &&
            socket &&
            sessionId &&
            participantId
          ) {
            const msg = {
              session_id: sessionId,
              participant_id: participantId,
              speaker: speakerLabel(participantId),
              text: text.trim(),
              timestamp: new Date().toISOString(),
            }
            console.log('[SpeechRecognizer] Auto-sending message:', msg)
            socket.emit('send_text', msg)
            setTextInput('')
          }
        } else {
          console.log('[SpeechRecognizer] Interim text:', text)
          setInterimText(text)
        }
      },
      onError: (error: string) => {
        console.error('[SpeechRecognizer] Error:', error)
        setListening(false)
      }
    })
    setSpeech(s)

    return () => {
      s.dispose()
    }
  }, [socket, sessionId, participantId, speakerLabel])

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
      setAnalyzing(false)
    })
    socket.on('segment_analyzed', (data) => {
      // shape: { session_id, segment_id, result }
      setAnalysisData(data.result)
      addSegment(data.result)
      setAnalyzing(false)
    })
    socket.on('segment_analyzed_integrated', (data) => {
      // shape: { session_id, segment_id, result }
      setAnalysisData(data.result)
      if (data.result?.base_analysis) {
        addSegment(data.result.base_analysis)
      }
      setAnalyzing(false)
    })

    // Task 5: Listen for updateIssue events with delta
    socket.on('updateIssue', (data) => {
      console.log('[DiscussionView] Received updateIssue delta:', {
        auto_triggered: data.auto_triggered,
        changed_nodes: data.changed_nodes?.length,
        changed_edges: data.changed_edges?.length,
        has_full_map: !!data.full_map,
      })
      
      // Use full_map if available for simpler updates
      if (data.full_map) {
        setAnalysisData((prev) => {
          if (!prev) return prev
          
          console.log('[DiscussionView] Applying full_map update')
          // Create completely new object with new issue_map reference
          // to ensure React detects the change
          return {
            ...prev,
            issue_map: {
              ...data.full_map,
              nodes: [...(data.full_map.nodes || [])],
              edges: [...(data.full_map.edges || [])],
              clusters: [...(data.full_map.clusters || [])],
            },
          }
        })
        return
      }

      // Apply delta to current analysis data
      setAnalysisData((prev) => {
        if (!prev) return prev
        
        console.log('[DiscussionView] Applying delta update')
        const updated = { ...prev }
        const issueMap = { ...(updated.issue_map || {}) }

        // Apply changed nodes
        const changedNodeIds = new Set(data.changed_nodes?.map((n: any) => n.id) || [])
        const newNodes = (issueMap.nodes?.filter((n: any) => !changedNodeIds.has(n.id)) || [])
        newNodes.push(...(data.changed_nodes || []))
        issueMap.nodes = newNodes

        // Apply changed edges
        const changedEdgeKeys = new Set(
          data.changed_edges?.map((e: any) => `${e.source}->${e.target}`) || []
        )
        const newEdges = (issueMap.edges?.filter(
          (e: any) => !changedEdgeKeys.has(`${e.source}->${e.target}`)
        ) || [])
        newEdges.push(...(data.changed_edges || []))
        issueMap.edges = newEdges

        // Remove deleted nodes
        if (data.deleted_node_ids?.length) {
          issueMap.nodes = issueMap.nodes?.filter(
            (n: any) => !data.deleted_node_ids.includes(n.id)
          )
        }

        // Remove deleted edges
        if (data.deleted_edge_ids?.length) {
          const deletedSet = new Set(
            data.deleted_edge_ids.map((e: any) => `${e[0]}->${e[1]}`)
          )
          issueMap.edges = issueMap.edges?.filter(
            (e: any) => !deletedSet.has(`${e.source}->${e.target}`)
          )
        }

        updated.issue_map = issueMap
        return updated
      })
    })

    return () => {
      socket.off('text_received')
      socket.off('analysis_result')
      socket.off('segment_analyzed')
      socket.off('segment_analyzed_integrated')
      socket.off('updateIssue')
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

  // Auto-run analysis when switching to topicmap tab
  useEffect(() => {
    if (activeTab === 'topicmap' && !analysisData && !analyzing && messages.length > 0) {
      console.log('[DiscussionView] Auto-running analysis for Topic Map')
      runAnalysis()
    }
  }, [activeTab, analysisData, analyzing, messages.length, runAnalysis])

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
    setTextInput('')
    speech.start()
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
            onClick={() => setActiveTab('analysis')}
            className={`px-4 py-2 font-medium border-b-2 transition ${
              activeTab === 'analysis'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            解析
          </button>
          <button
            onClick={() => setActiveTab('topicmap')}
            className={`px-4 py-2 font-medium border-b-2 transition ${
              activeTab === 'topicmap'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            トピックマップ
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

        {/* Analysis Tab */}
        {activeTab === 'analysis' && (
          <div className="h-full overflow-y-auto p-6">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">解析結果</h2>
                <button
                  onClick={runAnalysis}
                  disabled={messages.length === 0 || analyzing}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition flex items-center gap-2"
                >
                  {analyzing && <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" aria-label="loading" />}
                  {analyzing ? '解析中…' : '解析を実行'}
                </button>
              </div>

              {!analysisData ? (
                <div className="text-center py-12">
                  <p className="text-gray-500 mb-4">
                    セグメントを解析してください
                  </p>
                  <button
                    onClick={runAnalysis}
                    disabled={messages.length === 0 || analyzing}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition text-lg flex items-center justify-center gap-2"
                  >
                    {analyzing && <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" aria-label="loading" />}
                    {analyzing ? '解析中…' : '解析を実行'}
                  </button>
                </div>
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

                  {/* Participant prosody & states */}
                  {analysisData.participant_states && analysisData.participant_states.length > 0 && (
                    <div className="bg-white rounded-lg p-6 border border-gray-200">
                      <h3 className="text-lg font-semibold mb-4 text-gray-900">話者別・韻律と推定状態</h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                          <thead>
                            <tr className="text-left text-gray-600 border-b">
                              <th className="py-2 pr-4">話者</th>
                              <th className="py-2 pr-4">確信度</th>
                              <th className="py-2 pr-4">理解度</th>
                              <th className="py-2 pr-4">迷い</th>
                              <th className="py-2 pr-4">発話速度</th>
                              <th className="py-2 pr-4">ポーズ比率</th>
                              <th className="py-2 pr-4">言い淀み</th>
                            </tr>
                          </thead>
                          <tbody>
                            {analysisData.participant_states.map((p: any, idx: number) => (
                              <tr key={idx} className="border-b last:border-b-0">
                                <td className="py-2 pr-4 text-gray-900 font-medium">{p.speaker || 'Unknown'}</td>
                                <td className="py-2 pr-4">{Math.round((p.cognitive_state?.confidence_level || 0) * 100)}%</td>
                                <td className="py-2 pr-4">{Math.round((p.cognitive_state?.understanding_level || 0) * 100)}%</td>
                                <td className="py-2 pr-4">{Math.round((p.cognitive_state?.hesitation_level || 0) * 100)}%</td>
                                <td className="py-2 pr-4">{(p.prosody?.speech_rate || 0).toFixed(2)}</td>
                                <td className="py-2 pr-4">{Math.round((p.prosody?.pause_ratio || 0) * 100)}%</td>
                                <td className="py-2 pr-4">{p.prosody?.hesitation_count ?? 0}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Participant profiles */}
                  {analysisData.participant_profiles && Object.keys(analysisData.participant_profiles).length > 0 && (
                    <div className="bg-white rounded-lg p-6 border border-gray-200">
                      <h3 className="text-lg font-semibold mb-4 text-gray-900">話者プロファイル（傾向）</h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                          <thead>
                            <tr className="text-left text-gray-600 border-b">
                              <th className="py-2 pr-4">話者</th>
                              <th className="py-2 pr-4">発話スタイル</th>
                              <th className="py-2 pr-4">貢献スタイル</th>
                              <th className="py-2 pr-4">平均理解度</th>
                              <th className="py-2 pr-4">平均自信度</th>
                              <th className="py-2 pr-4">平均躊躇度</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.values(analysisData.participant_profiles).map((prof: any, idx: number) => (
                              <tr key={idx} className="border-b last:border-b-0">
                                <td className="py-2 pr-4 text-gray-900 font-medium">{prof.name || prof.participant_id || 'Unknown'}</td>
                                <td className="py-2 pr-4">{prof.speech_style}</td>
                                <td className="py-2 pr-4">{prof.contribution_style}</td>
                                <td className="py-2 pr-4">{Math.round(((prof.avg_metrics?.understanding) || 0) * 100)}%</td>
                                <td className="py-2 pr-4">{Math.round(((prof.avg_metrics?.confidence) || 0) * 100)}%</td>
                                <td className="py-2 pr-4">{Math.round(((prof.avg_metrics?.hesitation) || 0) * 100)}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

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

                  {/* Suggested Terms */}
                  <div className="bg-white rounded-lg p-6 border border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">💡 キー用語</h3>
                      <button
                        onClick={loadSuggestedTerms}
                        disabled={loadingTerms || messages.length === 0}
                        className="px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition text-sm flex items-center gap-2"
                      >
                        {loadingTerms && <span className="inline-block w-2 h-2 border-2 border-white border-t-transparent rounded-full animate-spin" aria-label="loading" />}
                        {loadingTerms ? '抽出中…' : '用語抽出'}
                      </button>
                    </div>

                    {suggestedTerms.length > 0 ? (
                      <div className="space-y-3">
                        {suggestedTerms.map((item: any, idx: number) => (
                          <div key={idx} className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-600">
                            <p className="font-semibold text-gray-900 mb-1">{item.term}</p>
                            <p className="text-sm text-gray-700">{item.definition}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-500 text-center py-6">用語抽出ボタンをクリックしてください</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Topic Map Tab */}
        {activeTab === 'topicmap' && (
          <div className="h-full flex flex-col bg-gradient-to-br from-blue-50 to-purple-50">
            <div className="flex-1 overflow-hidden flex flex-col">
              <div className="px-6 py-4 border-b border-gray-200 bg-white">
                <div className="flex items-center justify-between max-w-6xl mx-auto">
                  <h2 className="text-2xl font-bold text-gray-900">トピックマップ</h2>
                  <div className="text-sm text-gray-600">
                    React Flow ベースのリアルタイム編集
                  </div>
                </div>
              </div>

              {!analysisData?.issue_map ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center py-12 bg-white rounded-lg shadow-sm">
                    <p className="text-gray-500 mb-4">
                      解析を実行してIssue Mapを生成してください
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex-1 overflow-hidden">
                  <TopicMapEditor
                    issueMap={analysisData.issue_map}
                    editable={true}
                    socket={socket}
                    onChange={(updatedMap) => {
                      console.log('[DiscussionView] Topic Map edited:', updatedMap)
                      // TODO: Task 5 - emit updateIssue event to server
                    }}
                  />
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
