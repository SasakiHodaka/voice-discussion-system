# 音声議論システム Frontend

React + TypeScript + Socket.IO フロントエンド実装。

## ファイル構成

```
frontend/
  src/
    components/       # Reusable React components
    lib/
      api.ts          # API client
      store.ts        # Zustand state management
    pages/
      SessionDashboard.tsx    # Session creation/joining
      DiscussionView.tsx      # Main discussion interface
    App.tsx           # Main app component
    main.tsx          # Entry point
    index.css         # Global styles
  public/             # Static assets
  vite.config.ts      # Vite configuration
  package.json        # Dependencies
```

## セットアップ

### 1. 依存関係をインストール

```bash
cd frontend
npm ci
```

### 2. 開発サーバー起動

```bash
npm run dev
```

ブラウザで http://localhost:5173 にアクセス。

### 3. ビルド

```bash
npm run build
```

出力は `dist/` ディレクトリに生成されます。

## API 連携

フロントエンドは以下を通じてバックエンドと通信：

1. **REST API** (`/api/*`) - セッション管理、分析
2. **WebSocket** (`/socket.io`) - リアルタイム通信

開発時のプロキシ設定は `vite.config.ts` で定義。

## 環境変数

`.env.development` で設定：

```
VITE_API_BASE_URL=http://localhost:8000
```

## 主な機能

- セッション作成・参加
- リアルタイムメッセージング
- 会話分析結果の表示
- 参加者管理
