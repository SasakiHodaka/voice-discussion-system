# Test integrated analysis API

$testData = @{
    session_id = "67f0079a"
    segment_id = 1
    start_sec = 0.0
    end_sec = 30.0
    utterances = @(
        @{
            speaker = "Speaker1"
            text = "I think we should price the new product at 20,000 yen. Market research shows competitors average 18,000 yen, so this is a premium position."
            start = 0.0
            end = 10.0
        },
        @{
            speaker = "Speaker2"
            text = "I see, so you're pricing above competitors. What's the reasoning? Are you confident we have quality differentiation?"
            start = 10.0
            end = 20.0
        },
        @{
            speaker = "Speaker1"
            text = "Yes, exactly. We have three unique features that justify the premium price and give us competitive advantage."
            start = 20.0
            end = 30.0
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Sending test data to integrated analysis API..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/integrated/analyze-segment' `
        -Method POST `
        -Body $testData `
        -ContentType 'application/json' `
        -ErrorAction Stop
    
    Write-Host "`nIntegrated Analysis Results:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Write-Host
    
    # Extract key metrics
    if ($response.summary) {
        Write-Host "`n=== Analysis Summary ===" -ForegroundColor Cyan
        Write-Host "Discussion Health Score: $($response.summary.discussion_health)" -ForegroundColor White
        
        if ($response.summary.key_metrics) {
            Write-Host "`n=== Key Metrics ===" -ForegroundColor Cyan
            Write-Host "Confusion (M): $($response.summary.key_metrics.M)" -ForegroundColor White
            Write-Host "Stagnation (T): $($response.summary.key_metrics.T)" -ForegroundColor White
            Write-Host "Understanding (L): $($response.summary.key_metrics.L)" -ForegroundColor White
        }
    }
    
    # Check intervention needs
    if ($response.intervention) {
        Write-Host "`n=== Intervention Assessment ===" -ForegroundColor Cyan
        Write-Host "Intervention Needed: $($response.intervention.needed)" -ForegroundColor White
        if ($response.intervention.needed) {
            Write-Host "Type: $($response.intervention.type)" -ForegroundColor Yellow
            Write-Host "Priority: $($response.intervention.priority)" -ForegroundColor Yellow
            Write-Host "Message: $($response.intervention.message)" -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Host "Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.Response) {
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $errorContent = $reader.ReadToEnd()
        Write-Host "Details: $errorContent" -ForegroundColor Red
    }
}
