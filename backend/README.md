"""Backend README."""

# EchoMind Backend

FastAPI + SocketIO バックエンド実装。

## ファイル構成

```
backend/
  app/
    core/           # コア分析ロジック
      prompts/      # LLM プロンプトテンプレート
    models/         # Pydantic データモデル
    routers/        # REST API ルーター
    services/       # ビジネスロジック層
    sockets/        # SocketIO イベントハンドラー
    config.py       # 設定管理
    main.py         # FastAPI アプリケーション
  config.template.yaml  # 設定テンプレート
  pyproject.toml        # プロジェクト定義
  run.py               # 開発サーバー実行スクリプト
```

## セットアップ

### 1. 依存関係をインストール

```bash
cd backend
pip install -e .[dev]
```

### 2. 設定ファイルを作成

```bash
cp config.template.yaml config.yaml
# config.yaml を編集して OpenAI API キーなどを設定
```

### 3. 開発サーバーを起動

```bash
python run.py
```

またはポート番号を指定する場合：

```bash
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

ブラウザで http://localhost:8000 にアクセス。
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API

### REST エンドポイント

- `POST /api/sessions/` - セッション作成
- `GET /api/sessions/{session_id}` - セッション取得
- `POST /api/sessions/{session_id}/participants` - 参加者追加
- `POST /api/analysis/segment` - セグメント分析

### WebSocket イベント

- `join` - セッションに参加
- `send_text` - テキスト送信
- `analyze_segment` - セグメント分析
- `leave` - セッションから退出

## 既存パイプラインとの統合

現在のコードを参考に、以下の統合が実装されています：

1. `analysis_segment20.py` - セグメント分析ロジック
2. `viz_utils.py` - 可視化ユーティリティ
3. `echomind_pipeline_v2.py` - パイプライン処理

これらは `app/services/analysis.py` 経由でアクセス可能です。
