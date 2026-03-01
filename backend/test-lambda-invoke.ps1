$profile = "cerebrum"
$region = "eu-west-1"

$payload = @{
    path = "/api/analyze/AAPL"
    httpMethod = "GET"
    queryStringParameters = @{ stream = "false" }
    headers = @{}
} | ConvertTo-Json -Depth 5

$payload | Out-File -FilePath "lambda-payload.json" -Encoding UTF8

Write-Host "Invoking stock-analysis-analyzer Lambda directly..."
$start = Get-Date

aws lambda invoke `
    --function-name stock-analysis-analyzer `
    --payload file://lambda-payload.json `
    --profile $profile `
    --region $region `
    --log-type Tail `
    --cli-binary-format raw-in-base64-out `
    lambda-output.json 2>&1 | Out-String | Write-Host

$duration = (Get-Date) - $start
Write-Host "Duration: $([math]::Round($duration.TotalSeconds, 2))s"

Write-Host ""
Write-Host "=== Response ==="
if (Test-Path "lambda-output.json") {
    $response = Get-Content "lambda-output.json" | ConvertFrom-Json
    Write-Host ($response | ConvertTo-Json -Depth 5)
    Remove-Item "lambda-output.json"
}

if (Test-Path "lambda-payload.json") { Remove-Item "lambda-payload.json" }
