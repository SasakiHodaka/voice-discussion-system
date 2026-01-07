# セットアップガイド

このドキュメントに従えば、開発環境を完全にセットアップできます。

## 📋 前提条件

- Windows 10/11
- Git
- Python 3.13+
- Node.js 18+
- npm 9+

---

## 📁 プロジェクト構成

```
voice-discussion-system/
├── backend/                  # Python/FastAPI バックエンド
│   ├── app/
│   │   ├── main.py          # エントリポイント
│   │   ├── config.py        # CORS設定
│   │   ├── models/
│   │   │   └── schemas.py   # Pydantic モデル
│   │   ├── routers/
│   │   │   └── analysis.py  # 分析 API
│   │   ├── services/
│   │   │   └── full_analysis.py  # 分析ロジック
│   │   └── sockets/
│   │       └── handlers.py  # Socket.IO ハンドラ
│   ├── .venv/               # Python 仮想環境
│   └── requirements.txt      # 依存パッケージ
├── frontend/                 # React/Vite フロントエンド
│   ├── src/
│   │   ├── App.tsx          # ルートコンポーネント
│   │   ├── lib/
│   │   │   ├── api.ts       # API クライアント
│   │   │   └── speech.ts    # Web Speech API ラッパー
│   │   ├── pages/
│   │   │   ├── SessionDashboard.tsx  # セッション管理
│   │   │   └── DiscussionView.tsx    # 議論ビュー
│   │   ├── components/
│   │   │   └── AnalysisDashboard.tsx # 分析結果表示
│   │   └── store/
│   │       └── sessionStore.ts  # Zustand ストア
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── README.md                # プロジェクト説明
├── TROUBLESHOOTING.md       # トラブルシューティング
└── SETUP_GUIDE.md           # このファイル
```

---

## 🚀 セットアップ手順

### ステップ 1: リポジトリをクローン

```powershell
git clone https://github.com/SasakiHodaka/voice-discussion-system.git
cd voice-discussion-system
```

---

## 2️⃣ バックエンド（Python/FastAPI）

### ステップ 1: 仮想環境を作成

```powershell
cd backend

# 仮想環境を作成
python -m venv .venv

# 仮想環境を有効化
.venv\Scripts\Activate.ps1
```

**エラーが出た場合**: [トラブルシューティング - 仮想環境有効化](TROUBLESHOOTING.md#python--バックエンド)

### ステップ 2: 依存をインストール

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**インストールされるパッケージ**:
- FastAPI
- Uvicorn
- python-socketio
- python-multipart
- pydantic

### ステップ 3: バックエンドを起動

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**出力例**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
```

**API ドキュメント**: http://127.0.0.1:8000/docs

✅ バックエンド起動成功！

---

## 3️⃣ フロントエンド（React/Vite）

### ステップ 1: フロントエンドディレクトリに移動

```powershell
# backend ターミナルはそのままにして、別のターミナルで実行
cd frontend
```

### ステップ 2: PATH を更新（重要）

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
```

### ステップ 3: 依存をインストール

```powershell
npm install
```

**インストール内容**:
- React 18
- TypeScript 5
- Vite 5
- Tailwind CSS
- Zustand
- Axios
- socket.io-client

### ステップ 4: 開発サーバーを起動

```powershell
npm run dev
```

**出力例**:
```
VITE v5.4.21  ready in 297 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**ブラウザを開く**: http://localhost:5173/

✅ フロントエンド起動成功！

---

## 4️⃣ 動作確認

### ✅ チェックリスト

- [ ] バックエンド http://127.0.0.1:8000/docs にアクセス可能
- [ ] フロントエンド http://localhost:5173/ にアクセス可能
- [ ] UI が日本語で表示されている（「音声議論システム」）
- [ ] ブラウザコンソール（F12）に赤いエラーがない

### 🧪 簡単なテスト

1. **フロントエンド**: http://localhost:5173/ を開く
2. **チーム名入力**: 「チーム1」と入力
3. **セッション作成**: 「セッション作成」をクリック
4. **マイク許可**: ブラウザのマイクアクセス許可ダイアログで許可
5. **音声入力テスト**: スペースキーを長押ししてマイクをテスト
6. **分析実行**: 「全体分析を実行」をクリック

✅ すべてが動作すれば、セットアップ完了！

---

## 🔧 カスタマイズ

### バックエンド設定

[backend/app/config.py](backend/app/config.py):

```python
# CORS 設定（開発時）
CORS_ORIGINS = ["http://localhost:5173"]

# 本番環境では
# CORS_ORIGINS = ["https://yourdomain.com"]
```

### フロントエンド設定

[frontend/vite.config.ts](frontend/vite.config.ts):

```typescript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    }
  }
})
```

---

## 🚀 開発ワークフロー

### 日々の開発

```bash
# ターミナル1: バックエンド
cd backend
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# ターミナル2: フロントエンド
cd frontend
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
npm run dev

# ターミナル3: Git / 管理作業
cd .
git status
git add .
git commit -m "feat: new feature"
```

### ビルド（本番環境向け）

**フロントエンド**:
```powershell
cd frontend
npm run build  # dist/ に静的ファイルが生成される
```

**バックエンド**:
```powershell
# Gunicorn + Uvicorn で本番運用
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

---

## 🐛 よくある問題

詳細は [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

| 問題 | 解決 |
|------|------|
| `ModuleNotFoundError: No module named 'fastapi'` | 仮想環境を有効化して `pip install -r requirements.txt` |
| `npm: command not found` | PATH を再構成: `$env:Path = ...` |
| `Port 8000 already in use` | `Get-Process python \| Stop-Process -Force` で終了 |
| `CORS エラー` | backend/app/config.py で allow_origins を確認 |

---

## 📖 その他のリソース

- [FastAPI チュートリアル](https://fastapi.tiangolo.com/tutorial/)
- [React 公式ドキュメント](https://react.dev/)
- [TypeScript ハンドブック](https://www.typescriptlang.org/docs/)
- [Socket.IO クライアント API](https://socket.io/docs/v4/client-api/)
- [Vite ドキュメント](https://vitejs.dev/)

---

## 📞 サポート

セットアップがうまくいきませんか？ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を確認するか、GitHub Issues で質問をお待ちしています。

1. ターミナルのエラーメッセージを確認
2. `backend/` と `frontend/` の README.md を参照
3. バックエンドのログ出力を確認: `http://localhost:8000/docs`

---

**Happy discussing! 🚀**
