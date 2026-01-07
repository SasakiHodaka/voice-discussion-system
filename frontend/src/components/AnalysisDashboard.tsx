import React from 'react'
import { Users, MessageSquare, CheckCircle, XCircle, AlertTriangle, TrendingUp } from 'lucide-react'

interface FullAnalysisResult {
  session_id: string
  total_utterances: number
  speakers: string[]
  speaker_stats: Record<string, {
    utterance_count: number
    total_chars: number
    questions: number
    answers: number
    responses: number
  }>
  qa_matching: {
    ratio: number
    matched: number
    unmatched: number
  }
  topic_dispersion: number
  understanding_gaps: Array<{
    type: string
    severity: 'low' | 'medium' | 'high'
    description: string
  }>
  overall_quality: number
  metrics: {
    Q: number
    A: number
    R: number
    S: number
    X: number
  }
}

interface AnalysisDashboardProps {
  analysis: FullAnalysisResult | null
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ analysis }) => {
  if (!analysis) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500 text-center">分析結果がありません</p>
      </div>
    )
  }

  const quality = Math.max(0, Math.min(100, Math.round(analysis.overall_quality * 100)))
  const qaRatio = Math.round(analysis.qa_matching.ratio * 100)

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'text-red-600 bg-red-50'
      case 'medium': return 'text-yellow-600 bg-yellow-50'
      case 'low': return 'text-blue-600 bg-blue-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high': return <XCircle size={16} />
      case 'medium': return <AlertTriangle size={16} />
      case 'low': return <CheckCircle size={16} />
      default: return null
    }
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <MessageSquare size={18} />
            <span className="text-sm font-medium">発言数</span>
          </div>
          <p className="text-2xl font-bold">{analysis.total_utterances}</p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <Users size={18} />
            <span className="text-sm font-medium">話者数</span>
          </div>
          <p className="text-2xl font-bold">{analysis.speakers.length}</p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <CheckCircle size={18} />
            <span className="text-sm font-medium">Q-A一致率</span>
          </div>
          <p className="text-2xl font-bold">{qaRatio}%</p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <TrendingUp size={18} />
            <span className="text-sm font-medium">品質スコア</span>
          </div>
          <p className="text-2xl font-bold">{quality}%</p>
        </div>
      </div>

      {/* Speaker Contributions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">話者別貢献度</h3>
        <div className="space-y-4">
          {Object.entries(analysis.speaker_stats).map(([speaker, stats]) => {
            const totalUtterances = analysis.total_utterances
            const percentage = Math.round((stats.utterance_count / totalUtterances) * 100)
            
            return (
              <div key={speaker} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-700">{speaker}</span>
                  <span className="text-sm text-gray-500">{percentage}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-500"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <div className="flex gap-4 text-xs text-gray-600">
                  <span>質問: {stats.questions}</span>
                  <span>回答: {stats.answers}</span>
                  <span>応答: {stats.responses}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Q-A Matching Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">質疑応答の状況</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">質問数</p>
            <p className="text-2xl font-bold text-blue-600">{analysis.metrics.Q}</p>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">回答数</p>
            <p className="text-2xl font-bold text-green-600">{analysis.metrics.A}</p>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">未回答</p>
            <p className="text-2xl font-bold text-yellow-600">{analysis.qa_matching.unmatched}</p>
          </div>
        </div>
      </div>

      {/* Understanding Gaps */}
      {analysis.understanding_gaps.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold mb-4">理解のずれ・注意点</h3>
          <div className="space-y-3">
            {analysis.understanding_gaps.map((gap, idx) => (
              <div 
                key={idx}
                className={`flex items-start gap-3 p-3 rounded-lg ${getSeverityColor(gap.severity)}`}
              >
                <div className="mt-0.5">
                  {getSeverityIcon(gap.severity)}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-sm">{gap.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Additional Metrics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">詳細メトリクス</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center">
            <p className="text-xs text-gray-600 mb-1">質問 (Q)</p>
            <p className="text-xl font-bold">{analysis.metrics.Q}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-600 mb-1">回答 (A)</p>
            <p className="text-xl font-bold">{analysis.metrics.A}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-600 mb-1">応答 (R)</p>
            <p className="text-xl font-bold">{analysis.metrics.R}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-600 mb-1">沈黙 (S)</p>
            <p className="text-xl font-bold">{analysis.metrics.S}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-600 mb-1">中断 (X)</p>
            <p className="text-xl font-bold">{analysis.metrics.X}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AnalysisDashboard
