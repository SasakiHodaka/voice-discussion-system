# シナリオ3: 話者バランスの検出テスト

Write-Host ""
Write-Host "=" * 51 -ForegroundColor Cyan
Write-Host "  シナリオ3: 話者バランスの偏り検出" -ForegroundColor Yellow
Write-Host "=" * 51 -ForegroundColor Cyan
Write-Host ""

# セッション作成
Write-Host "[1/3] セッション作成..." -ForegroundColor Green
$session = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sessions/?title=Imbalance&description=Test" -Method POST
$sessionId = $session.session_id
Write-Host "  ✅ セッションID: $sessionId" -ForegroundColor Green

# 参加者Aが10回、B/Cが1回ずつの不均衡な発言
Write-Host ""
Write-Host "[2/3] 不均衡な議論を作成中..." -ForegroundColor Green
$imbalancedUtterances = @(
    @{ utterance_id="i1"; start=0.0; end=5.0; speaker="A"; text="私はこう思います。まず最初に考えるべきは" },
    @{ utterance_id="i2"; start=6.0; end=11.0; speaker="A"; text="次に重要なのはこの点です。具体的には" },
    @{ utterance_id="i3"; start=12.0; end=17.0; speaker="A"; text="さらにこの観点からも検討が必要です" },
    @{ utterance_id="i4"; start=18.0; end=23.0; speaker="A"; text="また別の視点として、こういった問題もあります" },
    @{ utterance_id="i5"; start=24.0; end=29.0; speaker="A"; text="そして最後に、この件についても述べておきたい" },
    @{ utterance_id="i6"; start=30.0; end=35.0; speaker="A"; text="加えて言えば、このアプローチも考えられます" },
    @{ utterance_id="i7"; start=36.0; end=41.0; speaker="A"; text="もう一つの重要な要素として" },
    @{ utterance_id="i8"; start=42.0; end=47.0; speaker="A"; text="総合的に判断すると、やはり" },
    @{ utterance_id="i9"; start=48.0; end=53.0; speaker="A"; text="結論としては、こうすべきだと思います" },
    @{ utterance_id="i10"; start=54.0; end=59.0; speaker="A"; text="以上が私の考えです。どうでしょうか" },
    @{ utterance_id="i11"; start=60.0; end=63.0; speaker="B"; text="なるほど..." },
    @{ utterance_id="i12"; start=64.0; end=67.0; speaker="C"; text="そうですね..." }
)

$analysisRequest = @{
    session_id = $sessionId
    segment_id = 1
    start_sec = 0.0
    end_sec = 67.0
    utterances = $imbalancedUtterances
} | ConvertTo-Json -Depth 10

$result = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/integrated/analyze-segment" `
    -Method POST -Body $analysisRequest -ContentType "application/json"

Write-Host "  ✅ 分析完了" -ForegroundColor Green

# 結果表示
Write-Host ""
Write-Host "[3/3] 分析結果" -ForegroundColor Green
Write-Host "─" * 51 -ForegroundColor Gray

# 発言回数カウント
$speakerCounts = @{}
foreach ($u in $imbalancedUtterances) {
    $s = $u.speaker
    if (-not $speakerCounts.ContainsKey($s)) {
        $speakerCounts[$s] = 0
    }
    $speakerCounts[$s]++
}

Write-Host "  発言回数:" -ForegroundColor Cyan
foreach ($k in $speakerCounts.Keys | Sort-Object) {
    Write-Host "    $k : $($speakerCounts[$k])回" -ForegroundColor Gray
}

$health = [math]::Round($result.summary.discussion_health * 100, 0)
Write-Host ""
Write-Host "  議論の健全性: $health%" -ForegroundColor $(if($health -lt 50){"Red"}else{"Yellow"})

if ($result.intervention.needed) {
    Write-Host ""
    Write-Host "  🚨 介入検出: $($result.intervention.type)" -ForegroundColor Red
    Write-Host "    優先度: $($result.intervention.priority)" -ForegroundColor Yellow
    Write-Host "    理由: $($result.intervention.reason)" -ForegroundColor Gray
    if ($result.intervention.message) {
        Write-Host "    メッセージ: $($result.intervention.message)" -ForegroundColor White
    }
} else {
    Write-Host ""
    Write-Host "  ✅ 介入不要" -ForegroundColor Green
}

Write-Host ""
Write-Host "─" * 51 -ForegroundColor Gray
Write-Host ""
