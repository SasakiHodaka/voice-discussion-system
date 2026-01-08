# 研究実装: 話者の特徴に基づく議論支援AI

## 概要

本実装は、修士研究計画書「話者の特徴に基づく議論支援AIの開発」に基づいて構築された、リアルタイム議論支援システムです。

## 研究の主要コンポーネント

### 1. 韻律情報分析 (`prosody_analysis.py`)

**目的**: 声の揺れや発話速度、言い淀みから参加者の認知状態を推定

**実装内容**:
- 発話速度の計算（モーラ/秒）
- 言い淀み検出（「えー」「あの」等）
- 語尾の曖昧化検出（「かな」「みたいな」等）
- ポーズ比率の推定
- 音声特徴からの迷い・確信度推定

**推定される認知状態**:
- `confidence_level`: 確信度 (0-1)
- `understanding_level`: 理解度 (0-1)
- `hesitation_level`: 迷いレベル (0-1)
- `engagement_level`: 議論への参加度 (0-1)
- `state_label`: 状態ラベル ("confident", "hesitant", "confused", "engaged")

### 2. 参加者特性モデリング (`participant_profile.py`)

**目的**: 複数回の議論から個人特性を抽出し、つまずきやすさを予測

**学習される特性**:
- 発言傾向（平均発言長、発話速度）
- 認知傾向（平均確信度、理解度、迷いレベル）
- つまずきやすいトピック
- 議論への貢献スタイル（質問型、回答型、提案型）

**活用方法**:
- 過去の履歴から特定トピックでの困難度を予測
- 参加者ごとの適切な支援タイミングを判断
- 個人に合わせた介入戦略の選択

### 3. 介入・助言生成 (`intervention.py`)

**目的**: 議論の状況に応じた適切な支援メッセージを生成

**介入タイプ**:
1. **明確化要求 (clarification)**: 議論が複雑化した際に定義や関係性の整理を促す
2. **要点整理 (summary)**: 参加者の理解度が低い際に重要ポイントを提示
3. **新しい視点 (perspective)**: 議論が停滞した際に別の角度からの問いかけ
4. **発言促進 (encouragement)**: 質問への回答や、発言が偏っている場合に促進

**介入判定基準**:
- 混乱度 (M) > 0.6
- 停滞度 (T) > 0.7
- 理解度 < 0.4 の参加者の存在
- 未回答の質問の存在
- 発言の極端な偏り (70%以上を一人が占める)

### 4. 統合分析サービス (`integrated_analysis.py`)

**目的**: 上記3つのコンポーネントを統合し、包括的な分析を提供

**処理フロー**:
1. 基本分析（EchoMindベースの議論構造分析）
2. 各発言の韻律分析と認知状態推定
3. 個人特性を考慮した予測
4. 介入必要性の判定
5. 必要に応じた介入メッセージ生成
6. 議論の健全性スコア計算

**出力される情報**:
```json
{
  "base_analysis": {/* 議論構造、Q/A/R/S/Xイベント */},
  "participant_states": [/* 各参加者の認知状態 */],
  "participant_predictions": {/* 個人特性に基づく予測 */},
  "intervention": {
    "needed": true,
    "type": "clarification",
    "priority": 0.8,
    "reason": "高い混乱度が検出されました",
    "message": "💡 議論が複雑になっています..."
  },
  "summary": {
    "discussion_health": 0.65,
    "cognitive_stats": {/* 全体平均 */},
    "key_metrics": {/* M, T, Lメトリクス */}
  }
}
```

## API エンドポイント

### 統合分析

```bash
POST /api/integrated/analyze-segment
```

**パラメータ**:
- `session_id`: セッションID
- `segment_id`: セグメントID
- `start_sec`: 開始時刻
- `end_sec`: 終了時刻
- `utterances`: 発言リスト

**レスポンス**: 統合分析結果（上記JSON参照）

### 参加者プロファイル

```bash
GET /api/integrated/participant-profile/{participant_id}
```

**レスポンス**:
```json
{
  "participant_id": "abc123",
  "name": "山田太郎",
  "speech_style": "詳細な説明型",
  "contribution_style": "質問主導型",
  "cognitive_tendency": ["自信を持って発言", "慎重に考えながら発言"],
  "confused_topics": ["技術詳細", "予算配分"],
  "confident_topics": ["全体方針", "スケジュール"],
  "total_sessions": 5,
  "avg_metrics": {
    "confidence": 0.72,
    "understanding": 0.68,
    "hesitation": 0.35
  }
}
```

### リアルタイム推奨アクション

```bash
POST /api/integrated/realtime-recommendations
```

**パラメータ**:
- `session_id`: セッションID
- `current_segment_result`: 現在のセグメント結果
- `participant_states`: 参加者の認知状態

**レスポンス**:
```json
{
  "recommendations": [
    {
      "type": "support_needed",
      "priority": "high",
      "participants": ["佐藤花子"],
      "action": "理解度が低い参加者がいます。説明を補足するか確認してください。"
    }
  ]
}
```

## WebSocket イベント

### `analyze_segment_integrated`

統合分析を実行し、結果を全参加者に配信

**送信**:
```javascript
socket.emit('analyze_segment_integrated', {
  session_id: 'session123',
  segment_id: 5,
  start_sec: 100.0,
  end_sec: 120.0,
  utterances: [...]
})
```

**受信**: `segment_analyzed_integrated`イベントで結果を受信

### `intervention_needed`

介入が必要な場合に自動配信

**受信**:
```javascript
socket.on('intervention_needed', (data) => {
  console.log('介入が必要:', data.intervention.message)
})
```

### `get_participant_insights`

参加者の特性インサイトを取得

**送信**:
```javascript
socket.emit('get_participant_insights', {
  participant_id: 'user123'
})
```

**受信**: `participant_insights`イベントで結果を受信

## フロントエンド統合

### IntegratedAnalysisPanel コンポーネント

統合分析結果を可視化する専用コンポーネント

**表示内容**:
1. **議論の健全性スコア**: 0-100%で表示、色分けで状態を視覚化
2. **参加者の認知状態**: 各参加者の確信度・理解度・迷いレベルをバーで表示
3. **介入メッセージ**: 優先度に応じた色分けと具体的なアドバイス
4. **主要メトリクス**: M（混乱度）、T（停滞度）、L（理解度）

**使用例**:
```tsx
import { IntegratedAnalysisPanel } from '@/components/IntegratedAnalysisPanel'

function DiscussionView() {
  const [analysisResult, setAnalysisResult] = useState(null)

  useEffect(() => {
    socket.on('segment_analyzed_integrated', (data) => {
      setAnalysisResult(data.result)
    })
  }, [])

  return (
    <div>
      {analysisResult && <IntegratedAnalysisPanel result={analysisResult} />}
    </div>
  )
}
```

## 研究の独自性

本実装は以下の点で既存研究と差別化されています:

1. **韻律情報の統合**: 発話内容だけでなく、話し方の特徴から認知状態を推定
2. **個人特性の学習**: 複数セッションからの学習により、個人差を考慮した支援
3. **リアルタイム介入**: 議論中に自動で問題を検出し、適切なタイミングで助言
4. **説明可能性**: 推定根拠を明示し、なぜその判断に至ったかを提示
5. **統合的アプローチ**: 議論構造・認知状態・個人特性を統合した分析フレーム

## 今後の拡張

総合研究で構築した前処理パイプラインを基盤とし、修士研究では以下を拡張予定:

1. **音声特徴の高度化**: librosaを用いた本格的な韻律特徴抽出
2. **機械学習モデルの導入**: 認知状態推定の精度向上
3. **長期的な学習**: より多くのセッションからのパターン抽出
4. **A/Bテスト**: 介入の効果測定と最適化
5. **マルチモーダル統合**: 表情や視線情報の統合（将来的）

## 参考文献

- EchoMind (CSCW 2025): https://github.com/atomiechen/EchoMind
- 本研究の設計思想: 議論中の「見えない理解の揺らぎ」を可視化し、適切な支援を行うこと
