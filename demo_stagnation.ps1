# シナリオ2: 停滞議論の検出テスト

Write-Host ""
Write-Host "=" * 51 -ForegroundColor Cyan
Write-Host "  シナリオ2: 停滞議論の検出" -ForegroundColor Yellow
Write-Host "=" * 51 -ForegroundColor Cyan
Write-Host ""

# セッション作成
Write-Host "[1/3] セッション作成..." -ForegroundColor Green
$session = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sessions/?title=Stagnation&description=Test" -Method POST
$sessionId = $session.session_id
Write-Host "  ✅ セッションID: $sessionId" -ForegroundColor Green

# 短くて迷いのある発言を連続して投入
Write-Host ""
Write-Host "[2/3] 停滞状態を作成中..." -ForegroundColor Green
$stagnantUtterances = @(
    @{ utterance_id="s1"; start=0.0; end=2.0; speaker="A"; text="えーと、どうですかね..." },
    @{ utterance_id="s2"; start=3.0; end=5.0; speaker="B"; text="まあ、そうですね..." },
    @{ utterance_id="s3"; start=6.0; end=8.0; speaker="C"; text="うーん、難しいかな..." },
    @{ utterance_id="s4"; start=9.0; end=11.0; speaker="A"; text="あの、もしかしたら..." },
    @{ utterance_id="s5"; start=12.0; end=14.0; speaker="B"; text="そうかもしれないですね..." },
    @{ utterance_id="s6"; start=15.0; end=17.0; speaker="C"; text="とりあえず、まあ..." }
)

$analysisRequest = @{
    session_id = $sessionId
    segment_id = 1
    start_sec = 0.0
    end_sec = 17.0
    utterances = $stagnantUtterances
} | ConvertTo-Json -Depth 10

$result = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/integrated/analyze-segment" `
    -Method POST -Body $analysisRequest -ContentType "application/json"

Write-Host "  ✅ 分析完了" -ForegroundColor Green

# 結果表示
Write-Host ""
Write-Host "[3/3] 分析結果" -ForegroundColor Green
Write-Host "─" * 51 -ForegroundColor Gray

$health = [math]::Round($result.summary.discussion_health * 100, 0)
Write-Host "  議論の健全性: $health%" -ForegroundColor $(if($health -lt 50){"Red"}else{"Yellow"})

Write-Host ""
Write-Host "  主要メトリクス:" -ForegroundColor Cyan
Write-Host "    混乱度(M): $($result.summary.key_metrics.confusion)" -ForegroundColor Gray
Write-Host "    停滞度(T): $($result.summary.key_metrics.stagnation)" -ForegroundColor Gray
Write-Host "    理解度(L): $($result.summary.key_metrics.understanding)" -ForegroundColor Gray

if ($result.intervention.needed) {
    Write-Host ""
    Write-Host "  🚨 介入検出: $($result.intervention.type)" -ForegroundColor Red
    Write-Host "    理由: $($result.intervention.reason)" -ForegroundColor Gray
    Write-Host "    メッセージ: $($result.intervention.message)" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "  ✅ 介入不要" -ForegroundColor Green
}

Write-Host ""
Write-Host "─" * 51 -ForegroundColor Gray
Write-Host ""
