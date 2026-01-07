# プロジェクト全体構造と参考実装ノート

本ドキュメントは、[atomiechen/EchoMind](https://github.com/atomiechen/EchoMind) を参考に実装した、
AI協働型ファシリテーションシステムの設計パターンと実装上の考慮事項をまとめたものです。

---

## 🏗️ アーキテクチャ概要

### レイヤー構成

```
┌──────────────────────────────────────┐
│   Frontend (React + TypeScript)      │
│   - UI コンポーネント                 │
│   - SocketIO リアルタイム通信        │
│   - REST API クライアント            │
└──────────────┬──────────────────────┘
               │
        HTTP / WebSocket
               │
┌──────────────▼──────────────────────┐
│   Backend (FastAPI + SocketIO)       │
│   ┌────────────────────────────────┐ │
│   │  REST API Layer                │ │
│   │  - Sessions                    │ │
│   │  - Analysis                    │ │
│   └────────────────────────────────┘ │
│   ┌────────────────────────────────┐ │
│   │  WebSocket Layer               │ │
│   │  - Real-time events            │ │
│   │  - Message broadcasting        │ │
│   └────────────────────────────────┘ │
│   ┌────────────────────────────────┐ │
│   │  Service Layer                 │ │
│   │  - SessionManager              │ │
│   │  - AnalysisService             │ │
│   │  - LLMService                  │ │
│   └────────────────────────────────┘ │
└──────────────┬──────────────────────┘
               │
         Analysis Logic
               │
┌──────────────▼──────────────────────┐
│   Existing Analysis Modules          │
│   - analysis_segment20.py            │
│   - echomind_pipeline_v2.py         │
│   - viz_utils.py                    │
└──────────────────────────────────────┘
```

---

## 📁 ファイル・ディレクトリ説明

### Backend (`backend/`)

#### 設定・初期化

- **`config.template.yaml`** - 設定テンプレート
  - LLM設定 (OpenAI キー、モデル選択)
  - ASR設定 (音声認識サービス URI)
  - セッション管理設定
  - ログレベル

- **`pyproject.toml`** - プロジェクト定義
  - 依存パッケージ管理
  - ビルド設定

- **`run.py`** - 開発サーバー起動スクリプト

#### コアアプリケーション (`app/`)

##### 設定管理 (`app/config.py`)

```python
class Settings:
    """すべての設定をまとめた中心的クラス"""
    server: ServerSettings
    llm: LLMSettings
    asr: ASRSettings
    ...
```

**特徴**:
- Pydantic `BaseSettings` 使用
- 環境変数との連携
- 型安全な設定管理

##### データモデル (`app/models/schemas.py`)

```python
# WebSocket メッセージモデル
class SocketMessage(BaseModel):
    type: MessageType
    session_id: str
    data: Dict[str, Any]

# セッションモデル
class DiscussionSessionModel(BaseModel):
    session_id: str
    participants: List[ParticipantModel]
    segments: List[SegmentResultModel]
```

**利点**:
- OpenAPI スキーマ自動生成
- クライアント側の型定義を共有可能
- バリデーション自動化

##### ビジネスロジック (`app/services/`)

###### セッション管理 (`session.py`, `session_advanced.py`)

```python
class SessionManager:
    """セッションのライフサイクル管理"""
    - create_session()         # 作成
    - add_participant()        # 参加者追加
    - add_segment_result()     # 分析結果保存
    - end_session()            # 終了
    - get_metrics()            # 統計情報取得
```

**機能**:
- メモリ上でのセッション管理
- セッション永続化 (JSON ファイル保存)
- タイムアウト自動削除
- 参加者統計の自動追跡

###### 分析サービス (`analysis.py`)

```python
class AnalysisService:
    """既存の分析モジュール統合"""
    analyze_segment()  # analysis_segment20.py との連携
```

**設計パターン**:
- 既存の Python モジュール (`analysis_segment20.py`) を動的インポート
- Pydantic モデルへの変換
- エラーハンドリングと Fallback

###### LLM サービス (`llm.py`)

```python
class LLMService:
    """LLM呼び出しと結果処理"""
    - classify_issues()        # 議題分類
    - generate_summary()       # サマリー生成
    - assess_quality()         # 品質評価
```

**統合ポイント**:
- プロンプトマネージャー (`prompts.py`) との連携
- OpenAI API へのアクセス
- 結果の JSON パース

##### WebSocket ハンドラー (`app/sockets/handlers.py`)

```python
@sio.event
async def join(sid: str, data: Dict) -> None:
    """参加者がセッションに参加"""
    # セッション参加処理
    # 他クライアントへの通知

@sio.event
async def analyze_segment(sid: str, data: Dict) -> None:
    """セグメント分析リクエスト"""
    # 分析実行
    # 結果をルーム内に broadcast
```

**SocketIO パターン**:
- `@sio.event` デコレーター使用
- 非同期処理 (`async/await`)
- ルーム単位でのメッセージ送信 (`sio.emit(..., room=session_id)`)

##### REST API ルーター (`app/routers/`)

###### Sessions Router (`sessions.py`)

```python
@router.post("/", response_model=DiscussionSessionModel)
async def create_session(...) -> DiscussionSessionModel:
    """セッション作成"""

@router.get("/{session_id}", response_model=DiscussionSessionModel)
async def get_session(session_id: str) -> DiscussionSessionModel:
    """セッション取得"""
```

**設計原則**:
- RESTful 原則に準拠
- 明示的な型ヒント
- 自動 OpenAPI スキーマ生成

##### プロンプト管理 (`app/core/prompts.py`, `app/core/prompts/*.hprompt`)

```python
class PromptManager:
    """HandyLLM フォーマット プロンプト管理"""
    render_prompt()  # テンプレート変数を埋める
```

**プロンプト構造** (`.hprompt`):

```yaml
---
version: 1
description: Issue classification
tags: [discussion]
---

You are an expert...

## Task
Analyze and classify...

## Output Format
```json
{ ... }
```

**利点**:
- EchoMind との一貫性
- 人間が読みやすい
- バージョン管理が容易

##### メインアプリケーション (`app/main.py`)

```python
app = FastAPI(...)

# CORS ミドルウェア
app.add_middleware(CORSMiddleware, ...)

# ルーター登録
app.include_router(sessions.router)
app.include_router(analysis.router)

# SocketIO 統合
app = ASGIApp(sio, ..., app)
```

**統合ポイント**:
- FastAPI と SocketIO の統合 (`ASGIApp`)
- CORS 設定
- 複数ルーターの登録

### Frontend (`frontend/`)

#### 設定ファイル

- **`vite.config.ts`** - Vite ビルドツール設定
  - バックエンド API へのプロキシ設定
  - ビルド出力設定

- **`tsconfig.json`** - TypeScript 設定
  - 厳密モード (`strict: true`)
  - パスマッピング (`@/*`)

- **`tailwind.config.js`** - Tailwind CSS 設定

#### ソースコード (`src/`)

##### ストア管理 (`lib/store.ts`)

```typescript
interface SessionStore {
    sessionId: string | null
    participantId: string | null
    participants: ParticipantModel[]
    segments: SegmentResultModel[]
    
    setSession()
    addParticipant()
    addSegment()
}

export const useSessionStore = create<SessionStore>(...)
```

**ツール**: Zustand（軽量状態管理）

**利点**:
- グローバル状態の集約
- コンポーネント間のデータ共有
- ローカル ストレージとの連携可能

##### API クライアント (`lib/api.ts`)

```typescript
const apiClient = axios.create({
    baseURL: `${API_BASE_URL}/api`,
})

export const sessionAPI = {
    createSession: async (data) => {...},
    getSession: async (sessionId) => {...},
    ...
}
```

**パターン**:
- Axios を用いた HTTP クライアント
- API エンドポイント単位でのグループ化
- 型安全な リクエスト/レスポンス

##### ページコンポーネント

###### SessionDashboard (`pages/SessionDashboard.tsx`)

```typescript
const SessionDashboard: React.FC = () => {
    const [sessions, setSessions] = useState<any[]>([])
    
    const handleCreateSession = async () => {
        const session = await sessionAPI.createSession(...)
        setSession(session.session_id, session.title)
    }
}
```

**フロー**:
1. セッション一覧を取得
2. 新規セッション作成 or 既存セッションに参加
3. Zustand ストアを更新

###### DiscussionView (`pages/DiscussionView.tsx`)

```typescript
const DiscussionView: React.FC = () => {
    useEffect(() => {
        socket.on('text_received', (data) => {
            setMessages([...messages, data])
        })
        socket.on('segment_analyzed', (data) => {
            setSegments([...segments, data.result])
        })
    }, [socket])
}
```

**リアルタイム機能**:
- SocketIO イベントリスナー登録
- リアルタイムメッセージ受信
- 分析結果の動的表示

---

## 🔄 データフロー

### セッション参加フロー

```
1. Frontend: "Create Session" ボタンクリック
   ↓
2. REST API POST /api/sessions/
   ↓
3. Backend: SessionManager.create_session()
   ↓
4. Frontend: setSession() を呼び出し
   ↓
5. Frontend: DiscussionView へ遷移
   ↓
6. WebSocket: join イベント送信
   ↓
7. Backend: SocketIO join ハンドラー実行
   ↓
8. Server → All Clients: participant_joined イベント
```

### リアルタイム分析フロー

```
1. Frontend: テキスト送信
   ↓
2. WebSocket: send_text イベント
   ↓
3. Backend: SocketIO send_text ハンドラー
   ↓
4. Server → All Clients: text_received イベント
   ↓
5. Frontend: 「Analyze Segment」ボタンクリック
   ↓
6. WebSocket: analyze_segment イベント
   ↓
7. Backend: 
   - analyze_segment() 呼び出し
   - AnalysisService を使用して分析実行
   - LLMService で追加分析 (オプション)
   ↓
8. Server → All Clients: segment_analyzed イベント
   ↓
9. Frontend: 結果を表示
```

---

## 🎯 EchoMind からの学習点

### 1. モジュール化

**参考**: EchoMind は以下のように構造化
```
backend/
  app/core/prompts/        ← プロンプト集約
  app/models/              ← データモデル集約
  app/routers/             ← API エンドポイント集約
```

**実装**: 同じパターンを採用

### 2. プロンプト管理

**参考**: HandyLLM フォーマット (`.hprompt`)
- バージョン管理
- メタデータ (description, tags)
- 人間が読みやすい書式

**実装**: `app/core/prompts/*.hprompt` として適用

### 3. リアルタイム通信

**参考**: Socket.IO でのルーム管理
```python
sio.enter_room(sid, session_id)
sio.emit('event', data, room=session_id)
```

**実装**: 同じパターンで複数ユーザー対応

### 4. 既存コード統合

**パターン**: 既存の `analysis_segment20.py` を動的インポート
```python
sys.path.insert(0, parent_dir)
from analysis_segment20 import analyze_segment
```

**メリット**:
- 既存ロジックの再利用
- 段階的リファクタリング
- Fallback オプション

---

## 💡 ベストプラクティス

### Backend

✅ **やるべき**

- Pydantic モデルで型安全性確保
- 非同期処理 (`async/await`) でスケーラビリティ確保
- エラーハンドリングと Fallback
- ログ記録の充実
- セッションの永続化

### Frontend

✅ **やるべき**

- コンポーネントの再利用可能な設計
- Zustand などの状態管理の活用
- TypeScript の型安全性を最大利用
- キーボードショートカットなどの UX 改善
- エラー状態の適切なハンドリング

### 全般

✅ **やるべき**

- ドキュメントの充実
- API スキーマの自動生成と同期
- テストの整備 (ユニットテスト、E2E テスト)
- CI/CD パイプライン
- バージョン管理

---

## 📝 実装上の注意事項

### 1. CORS 設定

```python
CORSMiddleware(
    allow_origins=settings.cors_origins,  # Whitelist 推奨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**注意**: 本番環境では厳格に設定

### 2. API キー管理

```python
api_key = os.getenv("OPENAI_API_KEY", "")  # 環境変数から
```

**注意**: `.env` ファイルを `.gitignore` に追加

### 3. セッションタイムアウト

```python
if self._is_expired(session):
    del self.sessions[session_id]
    return None
```

**効果**: メモリリーク防止

### 4. WebSocket 接続失敗時の Fallback

```typescript
const socket = io('...', {
    reconnection: true,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5,
})
```

---

## 🚀 今後の拡張案

### 短期 (1-2 週間)

- [ ] ユーザー認証 (JWT)
- [ ] データベース統合 (SQLAlchemy + PostgreSQL)
- [ ] セッション永続化の改善
- [ ] ユニットテスト

### 中期 (1-2 ヶ月)

- [ ] FunASR 統合 (音声認識)
- [ ] 議論ツリー可視化
- [ ] ビデオ・画面共有
- [ ] E2E テスト

### 長期 (3+ ヶ月)

- [ ] クラウドデプロイ (AWS, GCP)
- [ ] モバイルアプリ (React Native)
- [ ] プラグインシステム
- [ ] マルチ言語対応

---

**実装がお疲れ様でした！🎉**
