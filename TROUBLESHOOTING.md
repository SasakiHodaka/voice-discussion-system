# トラブルシューティングガイド

開発中に遭遇しやすい問題と解決方法をまとめました。

## 🐍 Python / バックエンド

### 問題1: Python プロセスが多重起動している / 無限ループ

**症状**: ターミナルが応答しない、または `python.exe` が大量に起動している

**原因**: Uvicorn の reload モードで同じファイルが何度も実行されている、または前の起動が完全に終了していない

**解決方法**:

```powershell
# 全ての Python プロセスを強制終了
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 念のため Node も終了
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
```

その後、バックエンドを再起動:

```powershell
cd backend
"C:/Users/sasakihodaka/AppData/Local/Programs/Python/Python313/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### 問題2: ModuleNotFoundError - 依存パッケージが見つからない

**症状**: `ModuleNotFoundError: No module named 'fastapi'` など

**原因**: Python 仮想環境が有効化されていない、または依存がインストールされていない

**解決方法**:

```powershell
cd backend

# 仮想環境を有効化
.venv\Scripts\Activate.ps1

# 依存をインストール
pip install -r requirements.txt

# 再度起動
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### 問題3: Port 8000 already in use

**症状**: `Address already in use` エラーが出る

**原因**: ポート 8000 が既に使われている

**解決方法**:

```powershell
# ポート 8000 を使用しているプロセスを確認
netstat -ano | Select-String "8000"

# PID を取得して強制終了
taskkill /PID <PID> /F

# または別のポートで起動
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

---

### 問題4: Socket.IO 404 エラー

**症状**: フロントエンドから `GET /socket.io/ 404` エラー

**原因**: FastAPI が Socket.IO namespace を提供していない、または ASGI ラッピングが不正

**確認**:

```bash
# バックエンドが起動しているか確認
curl http://127.0.0.1:8000/docs

# Socket.IO が応答しているか確認
curl http://127.0.0.1:8000/socket.io/
```

**解決方法**:

[backend/app/main.py](backend/app/main.py) で Socket.IO ASGI ラッピングを確認:

```python
from socketio import ASGIApp
socket_app = ASGIApp(sio, app)
```

---

## 📦 Node.js / フロントエンド

### 問題5: Node/npm コマンドが見つからない

**症状**: `npm: The term 'npm' is not recognized...`

**原因**: Node.js のパスが環境変数に登録されていない

**解決方法**:

```powershell
# Node のパスを確認
where node
where npm

# PATH を再構成して npm を実行
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
cd frontend
npm install
npm run dev
```

---

### 問題6: Port 5173 already in use / ポート競合

**症状**: Vite が起動しない、または `Port 5173 is in use`

**原因**: 前の Node プロセスがポートを解放していない

**解決方法**:

```powershell
# Node プロセスを全て終了
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

# 少し待機
Start-Sleep -Seconds 2

# 再起動
cd frontend
npm run dev
```

ポート確認:

```powershell
netstat -ano | Select-String "5173"
```

---

### 問題7: npm install が失敗する

**症状**: `npm ERR! code ERESOLVE` または `npm ERR! ERESOLVE unable to resolve dependency tree`

**原因**: 依存パッケージのバージョン競合

**解決方法**:

```powershell
cd frontend

# node_modules と package-lock.json を削除
Remove-Item -Recurse node_modules -ErrorAction SilentlyContinue
Remove-Item package-lock.json -ErrorAction SilentlyContinue

# キャッシュをクリア
npm cache clean --force

# 再インストール
npm install
```

---

### 問題8: Vite HMR（Hot Module Replacement）が動作しない

**症状**: ファイル変更後、自動リロードされない

**原因**: Vite 設定またはネットワーク接続の問題

**確認**:

1. ブラウザコンソール（F12）で WebSocket エラーを確認
2. `ws://localhost:5173/__vite_ping` が通信しているか確認

**解決方法**:

```powershell
# Vite 再起動
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
cd frontend
npm run dev
```

---

### 問題9: TypeScript コンパイルエラー

**症状**: `npm run type-check` が失敗する

**解決方法**:

```bash
cd frontend
npm run type-check  # エラー内容を確認
```

エラーの場所を特定して修正してから再度実行。

---

## 🌐 フロントエンド ↔ バックエンド通信

### 問題10: CORS エラーが出る

**症状**: ブラウザコンソール: `Access to XMLHttpRequest at 'http://127.0.0.1:8000/api/...' from origin 'http://localhost:5173' has been blocked by CORS policy`

**原因**: バックエンドの CORS 設定が不正

**確認**: [backend/app/config.py](backend/app/config.py) で以下を確認:

```python
allow_origins=["*"]  # 開発時はワイルドカード
allow_credentials=False  # ワイルドカード使用時は必ず False
```

---

### 問題11: Socket.IO 接続が確立されない

**症状**: ブラウザコンソール: `WebSocket connection to 'ws://127.0.0.1:8000/socket.io/...' failed`

**確認**:

1. バックエンド起動確認: `curl http://127.0.0.1:8000/docs`
2. ネットワークタブでリクエストを確認

**解決方法**:

```python
# backend/app/main.py で Socket.IO が正しく設定されているか確認
from socketio import ASGIApp, Server

sio = Server(async_mode='asgi', cors_allowed_origins='*')
socket_app = ASGIApp(sio, app)
```

---

## 🔄 Git/GitHub

### 問題12: Git プッシュが失敗する

**症状**: `fatal: not a git repository` または認証エラー

**解決方法**:

```powershell
# リポジトリ状態を確認
git status

# リモートを確認
git remote -v

# リモート URL が正しいか確認
git remote set-url origin https://github.com/SasakiHodaka/voice-discussion-system.git

# プッシュ
git push -u origin main
```

---

## 🔧 デバッグのコツ

### バックエンドのログを確認

```powershell
# 詳細ログ出力
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug
```

### フロントエンドのコンソールを確認

ブラウザで **F12** を押して **Console** タブを見る

### ネットワークリクエストを確認

ブラウザの **Network** タブで API 呼び出しを追跡

### Socket.IO デバッグ

```javascript
// frontend/src/lib/socket.ts に以下を追加
socket.onAny((event, ...args) => {
  console.log('Socket.IO event:', event, args);
});
```

---

## 📞 その他のリソース

- [FastAPI ドキュメント](https://fastapi.tiangolo.com/)
- [React ドキュメント](https://react.dev/)
- [Socket.IO ドキュメント](https://socket.io/)
- [Vite ドキュメント](https://vitejs.dev/)

---

**問題が解決されない場合**: GitHub Issues で報告してください。
