# リアルタイム トピックマップ実装サマリー

日時: 2026年1月9日  
目的: EchoMind 参考にして、リアルタイム議論ログから LLM ベースのトピックマップを自動生成する機能を実装

## 実装内容

### 1. **プロンプトファイル作成**
**ファイル**: `backend/app/core/prompts/realtime_issue_map.hprompt`

- HandyLLM 互換の `.hprompt` フォーマット
- **入力**: 議論の発話バッチ（speaker + text）
- **出力**: JSON 構造（nodes / edges / clusters）
- **特徴**:
  - 発話から 2-5 個のキートピック/問題を抽出
  - 6 つの分類カテゴリ：requirement, design, implementation, testing, schedule, resource
  - Q-A-R フローに基づく関係性（supports/questions/clarifies/contradicts/extends）
  - クラスタリングで視覚的グループ化

### 2. **バックエンド サービス拡張**
**ファイル**: `backend/app/services/issue_map.py`

#### 追加メソッド：
```python
def generate_issue_map_from_utterances(
    utterances: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """LLM ベースのマップ生成（リアルタイム用）"""
```

#### 補助メソッド：
- `_format_utterances_for_prompt()`: 発話を LLM 用テキストに整形
- `_parse_llm_response()`: LLM 応答から JSON を抽出
  - Triple backtick 形式対応
  - JSON パースエラー時のフォールバック

**動作フロー**:
1. LLM が利用可能かチェック
2. 発話をプロンプトにフォーマット
3. HandyLLM プロンプトをレンダリング（realtime_issue_map.hprompt）
4. LLM 呼び出し（OpenAI API 経由）
5. JSON パース → バリデーション
6. 失敗時は heuristic 版にフォールバック

### 3. **統合分析サービス更新**
**ファイル**: `backend/app/services/integrated_analysis.py`

```python
# 変更前（heuristic ベース）
issue_map = self.issue_map_service.generate_issue_map(
    events=base_result_dict.get("events", []),
    utterances=utterances,
)

# 変更後（LLM ベース優先）
try:
    issue_map = self.issue_map_service.generate_issue_map_from_utterances(
        utterances=utterances
    )
except Exception as e:
    logger.warning("LLM issue_map failed, using fallback: %s", e)
    issue_map = self.issue_map_service.generate_issue_map(...)
```

**効果**: リアルタイム分析時に自動的に LLM ベースのマップを優先生成

### 4. **Socket イベント（既存インテグレーション）**
**ファイル**: `backend/app/sockets/handlers.py`

- `analyze_segment_integrated` ハンドラが既に issue_map を `segment_analyzed_integrated` イベントで返却
- フロントエンドが自動的に受信して Topic Map タブに反映

```python
await sio.emit(
    "segment_analyzed_integrated",
    {
        "session_id": session_id,
        "segment_id": segment_id,
        "result": result,  # <- issue_map を含む
    },
    room=session_id,
)
```

### 5. **フロントエンド実装（既存）**
**ファイル**: `frontend/src/pages/DiscussionViewSimplified.tsx`

- Topic Map タブが `analysisData.issue_map` を読込
- ノードをクラスタ別に円形配置で可視化
- エッジで Q-A フローや関連性を表示
- 空時は「マップ生成中/十分なテキストが必要」メッセージ表示

## アーキテクチャ図

```
[会話入力] → [Socket: send_text]
                ↓
      [runAnalysis 呼び出し]
                ↓
    [Socket: analyze_segment_integrated]
                ↓
    [IntegratedAnalysisService]
                ↓
    [IssueMapService.generate_issue_map_from_utterances]
         ↓             ↓
    [LLM 呼び出し]  [フォールバック]
    (realtime_      (heuristic)
    issue_map)
         ↓
    [issue_map JSON]
         ↓
    [Socket: segment_analyzed_integrated]
         ↓
    [フロント: analysisData.issue_map 受信]
         ↓
    [Topic Map コンポーネント描画]
```

## 使用スタック

- **LLM**: OpenAI API (既存 config.yaml で設定)
- **プロンプト管理**: HandyLLM (.hprompt フォーマット)
- **通信**: Socket.IO (リアルタイム)
- **フロント**: React 18 + TypeScript (Topic Map 可視化)

## 設定要件

1. **OpenAI API キー**が `config.yaml` に設定されていること
   ```yaml
   llm:
     api_key: "sk-..."  # または環境変数 OPENAI_API_KEY
   ```

2. **HandyLLM** が依存として `pyproject.toml` に含まれていること（既存）

## テスト方法

```bash
# バックエンド テスト
cd backend
python test_issue_map_llm.py

# フロント テスト
1. Backend を起動: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
2. Frontend を起動: npm run dev
3. ブラウザで http://localhost:5173 にアクセス
4. チャットにテキスト送信
5. 「Topic Map」タブをクリック → 「解析を実行」
6. リアルタイムマップが描画される
```

## ログ確認

サーバーログで issue_map 生成を確認：

```
INFO: issue_map summary: nodes=3 edges=2 clusters=2 (segment=0)
```

ブラウザコンソールで issue_map 内容確認：

```javascript
// F12 開発者ツール → コンソール
console.log(analysisData.issue_map)
// {nodes: [{...}], edges: [{...}], clusters: [{...}]}
```

## 今後の拡張可能性

1. **差分更新**: 新規発話のみマップ更新する段階的更新
2. **リアルタイムストリーミング**: LLM ストリーミング応答で部分的描画
3. **ユーザ相互作用**: ノード名編集、手動エッジ追加/削除
4. **複数パターン生成**: 複数の LLM プロンプトバリアント試験
5. **永続化**: マップをセッション DB に保存し、振り返り機能強化

## トラブルシューティング

| 問題 | 原因 | 解決法 |
|------|------|--------|
| LLM エラー | OpenAI API キー不正 | `config.yaml` で `llm.api_key` を確認 |
| マップが空 | 発話が少なすぎる | 最低 3-4 発話必要；短い単語のみでは認識困難 |
| JSON パースエラー | LLM 応答形式がズレ | プロンプト修正; handyllm hprompt realtime_issue_map.hprompt で確認 |
| フロント表示されない | Socket 接続切断 | ブラウザコンソールで socket.io エラー確認 |

## ファイル一覧（変更/作成）

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/core/prompts/realtime_issue_map.hprompt` | 新規作成 |
| `backend/app/services/issue_map.py` | LLM 関数追加、import 拡張 |
| `backend/app/services/integrated_analysis.py` | LLM 優先呼び出しに変更 |
| `backend/test_issue_map_llm.py` | テストスクリプト新規作成 |
| `frontend/src/pages/DiscussionViewSimplified.tsx` | 既存 (変更なし) |
| `backend/app/sockets/handlers.py` | 既存 (変更なし) |

---

**実装完了日**: 2026年1月9日  
**ステータス**: ✅ 準備完了 → サーバー起動後テスト予定
