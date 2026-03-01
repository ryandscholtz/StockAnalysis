# Test Gateway Lambda Directly
$env:AWS_PROFILE = "Cerebrum"
$env:AWS_DEFAULT_REGION = "eu-west-1"

Write-Host "Testing stock-analysis-gateway Lambda..." -ForegroundColor Cyan
Write-Host ""

# Create test payload
$payload = @{
    resource = "/health"
    path = "/health"
    httpMethod = "GET"
    headers = @{}
    queryStringParameters = $null
    pathParameters = $null
    body = $null
    isBase64Encoded = $false
} | ConvertTo-Json -Compress

# Save to file (ASCII encoding to avoid BOM issues)
[System.IO.File]::WriteAllText("test-payload.json", $payload)

# Invoke Lambda
Write-Host "Invoking Lambda..." -ForegroundColor Yellow
aws lambda invoke `
    --function-name stock-analysis-gateway `
    --payload file://test-payload.json `
    --cli-binary-format raw-in-base64-out `
    response.json

Write-Host ""
Write-Host "Response:" -ForegroundColor Yellow
Get-Content response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Clean up
Remove-Item test-payload.json -ErrorAction SilentlyContinue
Remove-Item response.json -ErrorAction SilentlyContinue
