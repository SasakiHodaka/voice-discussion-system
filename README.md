# 音声議論システム（Voice Discussion System）

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.13+-blue)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue)](https://www.typescriptlang.org/)
[![SocketIO](https://img.shields.io/badge/Socket.IO-4+-red)](https://socket.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

リアルタイム音声入力と AI による自動分析を用いた、グループディスカッション支援システムです。EchoMind を参考に構築されています。

🔗 **参考**: [atomiechen/EchoMind](https://github.com/atomiechen/EchoMind) (CSCW 2025)

---

## ✨ 主な機能

### 🎯 リアルタイム議論支援

- **複数ユーザー対応** - 複数の参加者がリアルタイムで参加可能
- **リアルタイム同期** - WebSocket により議論内容をリアルタイム同期
- **セッション管理** - 議論セッションの作成・管理・保存

### 🧠 AI による分析

- **議題分類** - LLM による議題の自動分類と構造化
- **サマリー生成** - 議論内容の要約と アクションアイテムの生成
- **品質評価** - 議論の質と生産性を多次元で分析
- **メトリクス計算** - Q&A 頻度、混乱度、停滞度など

### 📊 可視化・レポート

- **セグメント分析マトリクス** - 時系列での議論パターン可視化
- **参加者統計** - 各参加者の貢献度計測
- **レポート生成** - Markdown/HTML による振り返りレポート

---

## 🏗️ システム構成

### バックエンド (FastAPI)

```python
app/
├── core/                    # コア分析・LLM機能
│   ├── prompts/            # HandyLLM形式 プロンプトテンプレート
│   └── prompts.py          # プロンプト管理
├── models/                  # Pydantic データモデル
├── routers/                 # REST API エンドポイント
├── services/
│   ├── session.py           # セッション管理
│   ├── analysis.py          # 分析サービス
│   └── llm.py              # LLM 統合
├── sockets/                 # WebSocket ハンドラー
├── config.py                # 設定管理
└── main.py                  # FastAPI アプリケーション
```

### フロントエンド (React + TypeScript)

```typescript
src/
├── components/              # React コンポーネント
├── pages/
│   ├── SessionDashboard.tsx    # セッション管理画面
│   └── DiscussionView.tsx      # 議論画面
├── lib/
│   ├── api.ts              # API クライアント
│   └── store.ts            # Zustand 状態管理
├── styles/                  # スタイルシート
├── App.tsx                  # ルートコンポーネント
└── main.tsx                 # エントリーポイント
```

---

## 🚀 クイックスタート

### 前提条件

- Python 3.9+
- Node.js 18+
- OpenAI API キー

### インストール

#### 1. バックエンド

```bash
cd backend
pip install -e .[dev]
cp config.template.yaml config.yaml
# config.yaml で OPENAI_API_KEY を設定
python run.py
```

#### 2. フロントエンド

別のターミナルで：

```bash
cd frontend
npm ci
npm run dev
```

ブラウザで http://localhost:5173 にアクセス。

#### 3. API ドキュメント

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📡 API & WebSocket

### REST エンドポイント

| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | `/api/sessions/` | セッション作成 |
| GET | `/api/sessions/{id}` | セッション取得 |
| POST | `/api/sessions/{id}/participants` | 参加者追加 |
| GET | `/api/sessions/{id}/segments` | 分析結果取得 |
| POST | `/api/analysis/segment` | セグメント分析 |

### WebSocket イベント

| イベント | 方向 | 説明 |
|---------|------|------|
| `join` | C→S | セッションに参加 |
| `send_text` | C→S | テキスト送信 |
| `analyze_segment` | C→S | セグメント分析リクエスト |
| `participant_joined` | S→C | 参加者参加通知 |
| `text_received` | S→C | テキスト受信通知 |
| `segment_analyzed` | S→C | 分析結果通知 |

詳細は [backend/API.md](backend/API.md) を参照。

---

## 🧠 LLM プロンプト

HandyLLM フォーマットで管理：

- `issue_classification.hprompt` - 議題分類
- `summary_generation.hprompt` - サマリー生成
- `quality_assessment.hprompt` - 品質評価

プロンプトのカスタマイズ:

```bash
handyllm hprompt backend/app/core/prompts/issue_classification.hprompt
```

---

## 📚 ドキュメント

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - 詳細なセットアップ手順
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - システムアーキテクチャと設計パターン
- **[backend/README.md](backend/README.md)** - バックエンド詳細
- **[backend/API.md](backend/API.md)** - API 仕様書
- **[frontend/README.md](frontend/README.md)** - フロントエンド詳細

---

## 🛠️ 開発

### テスト

```bash
cd backend
pytest tests/
```

### Linting & Type Check

```bash
cd backend
ruff check app/
mypy app/

cd frontend
npm run lint
npm run type-check
```

### ビルド

```bash
# Backend
cd backend
# (Docker でビルド)

# Frontend
cd frontend
npm run build
# dist/ に出力
```

---

## 🔐 セキュリティ

本番環境での推奨事項：

- [ ] ユーザー認証の実装 (JWT)
- [ ] HTTPS の有効化
- [ ] API キーの安全な管理 (環境変数)
- [ ] CORS の厳密設定
- [ ] レート制限の実装
- [ ] 入力値バリデーション
- [ ] ログの安全な保存

---

## 📊 分析メトリクス

各セグメント (20秒) で計算：

| メトリクス | 説明 | 範囲 |
|-----------|------|------|
| Q | 質問数 | 0+ |
| A | 回答数 | 0+ |
| UQ | 未回答質問数 | 0+ |
| R | 反論・異議数 | 0+ |
| M | 混乱度スコア | 0-1 |
| T | 停滞度スコア | 0-1 |
| L | 理解度スコア | 0-1 |

---

## 🌍 今後の拡張

### Short-term
- [ ] ユーザー認証
- [ ] データベース統合
- [ ] より詳細なテスト

### Mid-term
- [ ] 音声認識 (FunASR)
- [ ] ビデオ・画面共有
- [ ] 議論ツリー可視化
- [ ] ファイルエクスポート (PDF, CSV)

### Long-term
- [ ] クラウドデプロイ
- [ ] モバイルアプリ
- [ ] マルチ言語対応
- [ ] プラグインシステム

---

## 📝 引用・参考

### 論文

Chen, W., Yu, C., Wang, Y., et al. (2025). "EchoMind: Supporting Real-time Complex Problem Discussions through Human-AI Collaborative Facilitation." *Proc. ACM Hum.-Comput. Interact.* 9, 7, Article CSCW406.

https://doi.org/10.1145/3757587

### 関連プロジェクト

- [atomiechen/EchoMind](https://github.com/atomiechen/EchoMind) - 元のオープンソース実装
- [FastAPI](https://fastapi.tiangolo.com/)
- [Socket.IO](https://socket.io/)
- [React](https://react.dev/)

---

## 📄 ライセンス

このプロジェクトは、EchoMind を参考に実装されました。

---

## ❓ サポート

問題が発生した場合：

1. [SETUP_GUIDE.md](SETUP_GUIDE.md) の トラブルシューティング を確認
2. [ARCHITECTURE.md](ARCHITECTURE.md) で設計パターンを確認
3. ターミナルのエラーメッセージを確認
4. ブラウザの開発者ツール (F12) でネットワークエラーを確認

---

**Happy discussing! 🚀**

Made with ❤️ as a reference to EchoMind
