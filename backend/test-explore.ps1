$payload = @{
    path = "/api/explore/stocks"
    httpMethod = "GET"
    headers = @{}
    queryStringParameters = @{ market = "DOW30"; force_refresh = "true" }
    body = $null
} | ConvertTo-Json -Compress

$payload | Out-File -FilePath "test-explore-payload.json" -Encoding ascii

Write-Host "Invoking Lambda (may take 30-60s for yfinance to fetch 30 stocks)..." -ForegroundColor Yellow

aws lambda invoke `
    --function-name stock-analysis-stock-data `
    --payload file://test-explore-payload.json `
    --profile Cerebrum --region eu-west-1 `
    --cli-binary-format raw-in-base64-out `
    test-explore-result.json 2>&1

$result = Get-Content test-explore-result.json | ConvertFrom-Json
$body = $result.body | ConvertFrom-Json

if ($body.PSObject.Properties['stocks']) {
    Write-Host "OK - $($body.stocks.Count) stocks fetched, cached=$($body.cached)" -ForegroundColor Green
    if ($body.stocks.Count -gt 0) {
        Write-Host "Sample:" -ForegroundColor Cyan
        $body.stocks[0] | ConvertTo-Json
    }
} elseif ($body.error) {
    Write-Host "ERROR: $($body.error)" -ForegroundColor Red
} else {
    Write-Host "Response body: $($result.body.Substring(0, [Math]::Min(500, $result.body.Length)))"
}

Remove-Item test-explore-payload.json, test-explore-result.json -ErrorAction SilentlyContinue
