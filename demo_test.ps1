# デモテスト自動化スクリプト

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan
Write-Host "  研究デモ: 統合分析システムテスト" -ForegroundColor Yellow
Write-Host "=" * 51 -ForegroundColor Cyan
Write-Host ""

# ステップ1: セッション作成
Write-Host "[1/5] セッション作成中..." -ForegroundColor Green
$sessionUrl = "http://127.0.0.1:8000/api/sessions/?title=Demo&description=Test"
try {
    $session = Invoke-RestMethod -Uri $sessionUrl -Method POST -ErrorAction Stop
    $sessionId = $session.session_id
    Write-Host "  ✅ セッションID: $sessionId" -ForegroundColor Green
} catch {
    Write-Host "  ❌ エラー: $_" -ForegroundColor Red
    exit 1
}

# ステップ2: テスト発言データの準備
Write-Host ""
Write-Host "[2/5] テスト発言データ準備中..." -ForegroundColor Green

$testUtterances = @(
    @{
        utterance_id = "u1"
        start = 0.0
        end = 5.0
        speaker = "参加者A"
        text = "えーと、その、この提案についてなんですけど、ちょっとよくわからないところがあるんですよね"
    },
    @{
        utterance_id = "u2"
        start = 6.0
        end = 12.0
        speaker = "参加者B"
        text = "具体的にはどの部分ですか？詳しく説明しましょう"
    },
    @{
        utterance_id = "u3"
        start = 13.0
        end = 20.0
        speaker = "参加者A"
        text = "あの、まあ、競合との関係とか、なんか、どういう基準で決めるのかなって感じで..."
    },
    @{
        utterance_id = "u4"
        start = 21.0
        end = 30.0
        speaker = "参加者C"
        text = "つまり、価格設定の基準を明確にしたいということですね。例えば、原価積算方式と競合価格追従方式の2つのアプローチがあります"
    }
)

Write-Host "  ✅ 発言数: $($testUtterances.Count)" -ForegroundColor Green

# ステップ3: 統合分析の実行
Write-Host ""
Write-Host "[3/5] 統合分析実行中..." -ForegroundColor Green

$analysisRequest = @{
    session_id = $sessionId
    segment_id = 1
    start_sec = 0.0
    end_sec = 30.0
    utterances = $testUtterances
} | ConvertTo-Json -Depth 10

$analysisResult = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/integrated/analyze-segment" `
    -Method POST `
    -Body $analysisRequest `
    -ContentType "application/json"

Write-Host "  ✅ 分析完了" -ForegroundColor Green

# ステップ4: 結果の表示
Write-Host ""
Write-Host "[4/5] 分析結果表示" -ForegroundColor Green
Write-Host "─" * 51 -ForegroundColor Gray

# 議論の健全性
$health = $analysisResult.summary.discussion_health
$healthPercent = [math]::Round($health * 100, 0)
$healthColor = if ($health -ge 0.7) { "Green" } elseif ($health -ge 0.4) { "Yellow" } else { "Red" }
Write-Host "  議論の健全性: " -NoNewline
Write-Host "$healthPercent%" -ForegroundColor $healthColor

# 参加者の認知状態
Write-Host ""
Write-Host "  参加者の認知状態:" -ForegroundColor Cyan
foreach ($state in $analysisResult.participant_states) {
    $speaker = $state.speaker
    $cogState = $state.cognitive_state
    $confidence = [math]::Round($cogState.confidence_level * 100, 0)
    $understanding = [math]::Round($cogState.understanding_level * 100, 0)
    $hesitation = [math]::Round($cogState.hesitation_level * 100, 0)
    
    Write-Host "    $speaker [$($cogState.state_label)]" -ForegroundColor Yellow
    Write-Host "      確信度: $confidence% | 理解度: $understanding% | 迷い: $hesitation%" -ForegroundColor Gray
}

# 介入判定
Write-Host ""
$intervention = $analysisResult.intervention
if ($intervention.needed) {
    $priorityColor = if ($intervention.priority -gt 0.7) { "Red" } elseif ($intervention.priority -gt 0.5) { "Yellow" } else { "Cyan" }
    Write-Host "  🚨 介入が必要です" -ForegroundColor $priorityColor
    Write-Host "    タイプ: $($intervention.type)" -ForegroundColor Gray
    Write-Host "    優先度: $($intervention.priority)" -ForegroundColor Gray
    Write-Host "    理由: $($intervention.reason)" -ForegroundColor Gray
    if ($intervention.message) {
        Write-Host ""
        Write-Host "  📝 介入メッセージ:" -ForegroundColor Magenta
        Write-Host "    $($intervention.message)" -ForegroundColor White
    }
} else {
    Write-Host "  ✅ 介入不要（議論は順調です）" -ForegroundColor Green
}

# 主要メトリクス
Write-Host ""
Write-Host "  主要メトリクス:" -ForegroundColor Cyan
$metrics = $analysisResult.summary.key_metrics
Write-Host "    混乱度(M): $($metrics.confusion)" -ForegroundColor Gray
Write-Host "    停滞度(T): $($metrics.stagnation)" -ForegroundColor Gray
Write-Host "    理解度(L): $($metrics.understanding)" -ForegroundColor Gray

Write-Host ""
Write-Host "─" * 51 -ForegroundColor Gray

# ステップ5: ブラウザで確認
Write-Host ""
Write-Host "[5/5] ブラウザで確認" -ForegroundColor Green
Write-Host "  セッションID '$sessionId' でブラウザからアクセスできます" -ForegroundColor Cyan
Write-Host "  URL: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "=" * 51 -ForegroundColor Cyan
Write-Host "  テスト完了！" -ForegroundColor Yellow
Write-Host "=" * 51 -ForegroundColor Cyan
