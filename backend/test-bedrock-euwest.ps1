$profile = "cerebrum"
$region = "eu-west-1"
$modelId = "anthropic.claude-3-haiku-20240307-v1:0"

Write-Host "Testing Bedrock Claude 3 Haiku in eu-west-1..."

$body = @{
    anthropic_version = "bedrock-2023-05-31"
    max_tokens = 50
    messages = @(@{role = "user"; content = "Say hello in JSON: {`"greeting`": `"hello`"}"})
} | ConvertTo-Json -Depth 5

$body | Out-File -FilePath "test-bedrock-body.json" -Encoding UTF8

try {
    $result = aws bedrock-runtime invoke-model `
        --model-id $modelId `
        --body file://test-bedrock-body.json `
        --content-type "application/json" `
        --accept "application/json" `
        --profile $profile `
        --region $region `
        --output json `
        test-bedrock-response.json 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS! Bedrock responded:"
        Get-Content test-bedrock-response.json
    } else {
        Write-Host "FAILED with exit code $LASTEXITCODE"
        Write-Host $result
    }
} catch {
    Write-Host "Exception: $_"
} finally {
    if (Test-Path "test-bedrock-body.json") { Remove-Item "test-bedrock-body.json" }
    if (Test-Path "test-bedrock-response.json") { Remove-Item "test-bedrock-response.json" }
}
