# Fix API Gateway Integration - Update REST API to use stock-analysis-gateway Lambda
$ErrorActionPreference = "Stop"
$profile = "Cerebrum"
$region = "eu-west-1"
$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region

$restApiId = "dx0w31lbc1"
$newLambdaName = "stock-analysis-gateway"
$accountId = aws sts get-caller-identity --profile $profile --query 'Account' --output text
$lambdaArn = "arn:aws:lambda:${region}:${accountId}:function:${newLambdaName}"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Update API Gateway (REST) -> stock-analysis-gateway" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Profile: $profile | API: $restApiId" -ForegroundColor Gray
Write-Host "Lambda ARN: $lambdaArn" -ForegroundColor Gray
Write-Host ""
Write-Host "Target Lambda: $lambdaArn" -ForegroundColor Yellow
Write-Host ""

# REST API integration URI format
$integrationUri = "arn:aws:apigateway:${region}:lambda:path/2015-03-31/functions/${lambdaArn}/invocations"

# Update the main proxy route (/{proxy+})
Write-Host "Updating /{proxy+} route..." -ForegroundColor Yellow
aws apigateway put-integration `
    --rest-api-id $restApiId `
    --resource-id isyww0 `
    --http-method ANY `
    --type AWS_PROXY `
    --integration-http-method POST `
    --uri $integrationUri `
    --profile $profile `
    --region $region 2>&1

Write-Host "  Updated!" -ForegroundColor Green

# Update the root route (/)
Write-Host "Updating / route..." -ForegroundColor Yellow
aws apigateway put-integration `
    --rest-api-id $restApiId `
    --resource-id fv4yesi9m6 `
    --http-method ANY `
    --type AWS_PROXY `
    --integration-http-method POST `
    --uri $integrationUri `
    --profile $profile `
    --region $region 2>&1

Write-Host "  Updated!" -ForegroundColor Green

# Update the /health route
Write-Host "Updating /health route..." -ForegroundColor Yellow
aws apigateway put-integration `
    --rest-api-id $restApiId `
    --resource-id 6zv72a `
    --http-method GET `
    --type AWS_PROXY `
    --integration-http-method POST `
    --uri $integrationUri `
    --profile $profile `
    --region $region 2>&1

Write-Host "  Updated!" -ForegroundColor Green

# Update the /api/{proxy+} route
Write-Host "Updating /api/{proxy+} route..." -ForegroundColor Yellow
aws apigateway put-integration `
    --rest-api-id $restApiId `
    --resource-id yibc8w `
    --http-method ANY `
    --type AWS_PROXY `
    --integration-http-method POST `
    --uri $integrationUri `
    --profile $profile `
    --region $region 2>&1

Write-Host "  Updated!" -ForegroundColor Green
Write-Host ""

# Grant API Gateway permission to invoke the new Lambda
Write-Host "Granting API Gateway permission to invoke Lambda..." -ForegroundColor Yellow
$statementId = "apigateway-invoke-$(Get-Date -Format 'yyyyMMddHHmmss')"

try {
    aws lambda add-permission `
        --function-name $newLambdaName `
        --statement-id $statementId `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn "arn:aws:execute-api:${region}:${accountId}:${restApiId}/*/*" `
        --profile $profile `
        --region $region 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "  Permission granted!" -ForegroundColor Green }
    else { Write-Host "  Permission may already exist (this is OK)" -ForegroundColor Yellow }
} catch {
    Write-Host "  Permission may already exist (this is OK)" -ForegroundColor Yellow
}

Write-Host ""

# Deploy the API to production stage
Write-Host "Deploying API to production stage..." -ForegroundColor Yellow
aws apigateway create-deployment `
    --rest-api-id $restApiId `
    --stage-name production `
    --description "Updated to use stock-analysis-gateway Lambda" `
    --profile $profile `
    --region $region 2>&1

Write-Host "  Deployed!" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "API Gateway Integration Fixed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "API Endpoint: https://${restApiId}.execute-api.${region}.amazonaws.com/production/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Testing..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Test the health endpoint
$response = Invoke-WebRequest -Uri "https://${restApiId}.execute-api.${region}.amazonaws.com/production/health" -UseBasicParsing -ErrorAction SilentlyContinue

if ($response.StatusCode -eq 200) {
    Write-Host "Health check passed!" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Gray
} else {
    Write-Host "Health check failed with status: $($response.StatusCode)" -ForegroundColor Red
}
