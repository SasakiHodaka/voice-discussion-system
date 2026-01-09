# 統合分析のテストスクリプト

$testData = @{
    session_id = "67f0079a"
    segment_id = 1
    start_sec = 0.0
    end_sec = 30.0
    utterances = @(
        @{
            speaker = "田中"
            text = "新製品の価格を2万円に設定したいと思います。市場調査の結果、競合他社の平均が1.8万円でしたので、少し高めの設定です。"
            start = 0.0
            end = 10.0
        },
        @{
            speaker = "佐藤"
            text = "なるほど、競合より高めですね。その理由は何ですか？品質で差別化できると考えているのでしょうか。"
            start = 10.0
            end = 20.0
        },
        @{
            speaker = "田中"
            text = "はい、その通りです。独自機能が3つあるので、プレミアム価格でも十分に競争力があります。"
            start = 20.0
            end = 30.0
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "テストデータを送信中..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/integrated/analyze-segment' `
        -Method POST `
        -Body $testData `
        -ContentType 'application/json' `
        -ErrorAction Stop
    
    Write-Host "`n統合分析結果:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Write-Host
    
    # 主要メトリクスの抽出
    if ($response.summary) {
        Write-Host "`n【分析サマリー】" -ForegroundColor Cyan
        Write-Host "議論の健全性スコア: $($response.summary.discussion_health)" -ForegroundColor White
        
        if ($response.summary.key_metrics) {
            Write-Host "`n【メトリクス】" -ForegroundColor Cyan
            Write-Host "混乱度 (M): $($response.summary.key_metrics.M)" -ForegroundColor White
            Write-Host "停滞度 (T): $($response.summary.key_metrics.T)" -ForegroundColor White
            Write-Host "理解度 (L): $($response.summary.key_metrics.L)" -ForegroundColor White
        }
    }
    
    # 介入の必要性
    if ($response.intervention) {
        Write-Host "`n【介入必要性】" -ForegroundColor Cyan
        Write-Host "必要: $($response.intervention.needed)" -ForegroundColor White
        if ($response.intervention.needed) {
            Write-Host "タイプ: $($response.intervention.type)" -ForegroundColor Yellow
            Write-Host "優先度: $($response.intervention.priority)" -ForegroundColor Yellow
            Write-Host "メッセージ: $($response.intervention.message)" -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Host "エラーが発生しました:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.Response) {
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $errorContent = $reader.ReadToEnd()
        Write-Host "詳細: $errorContent" -ForegroundColor Red
    }
}
