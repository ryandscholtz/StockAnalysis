# Update API Gateway to use stock-analysis-gateway Lambda
$ErrorActionPreference = "Stop"
$profile = "Cerebrum"
$region = "eu-west-1"
$apiId = "dx0w31lbc1"
$lambdaName = "stock-analysis-gateway"

$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Update API Gateway -> stock-analysis-gateway" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Profile: $profile | Region: $region" -ForegroundColor Gray
Write-Host ""

# Get Lambda ARN
Write-Host "Getting Lambda ARN..." -ForegroundColor Yellow
$lambdaArn = aws lambda get-function `
    --function-name $lambdaName `
    --profile $profile `
    --region $region `
    --query 'Configuration.FunctionArn' `
    --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Could not get Lambda ARN" -ForegroundColor Red
    exit 1
}

Write-Host "Lambda ARN: $lambdaArn" -ForegroundColor Gray
Write-Host ""

# Get all routes
Write-Host "Getting API Gateway routes..." -ForegroundColor Yellow
$routes = aws apigatewayv2 get-routes `
    --api-id $apiId `
    --profile $profile `
    --region $region `
    --query 'Items[].{RouteId:RouteId,RouteKey:RouteKey,Target:Target}' `
    --output json | ConvertFrom-Json

Write-Host "Found $($routes.Count) routes" -ForegroundColor Gray
Write-Host ""

# Get existing integration ID from the first route
$existingIntegrationId = $null
if ($routes.Count -gt 0 -and $routes[0].Target) {
    $existingIntegrationId = $routes[0].Target -replace 'integrations/', ''
    Write-Host "Existing Integration ID: $existingIntegrationId" -ForegroundColor Gray
}

# HTTP API (v2) uses Lambda ARN directly as integration-uri
$integrationUri = $lambdaArn.Trim()

# Update or create integration
if ($existingIntegrationId) {
    Write-Host "Updating existing integration to stock-analysis-gateway..." -ForegroundColor Yellow
    aws apigatewayv2 update-integration `
        --api-id $apiId `
        --integration-id $existingIntegrationId `
        --integration-uri $integrationUri `
        --profile $profile `
        --region $region 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: update-integration failed. Trying with payload-format-version..." -ForegroundColor Yellow
        aws apigatewayv2 update-integration `
            --api-id $apiId `
            --integration-id $existingIntegrationId `
            --integration-uri $integrationUri `
            --payload-format-version "2.0" `
            --profile $profile `
            --region $region
    }
    
    $integrationId = $existingIntegrationId
} else {
    Write-Host "Creating new integration..." -ForegroundColor Yellow
    $integration = aws apigatewayv2 create-integration `
        --api-id $apiId `
        --integration-type AWS_PROXY `
        --integration-uri $integrationUri `
        --payload-format-version "2.0" `
        --profile $profile `
        --region $region | ConvertFrom-Json
    
    $integrationId = $integration.IntegrationId
    
    # Update all routes to use new integration
    Write-Host "Updating routes..." -ForegroundColor Yellow
    foreach ($route in $routes) {
        aws apigatewayv2 update-route `
            --api-id $apiId `
            --route-id $route.RouteId `
            --target "integrations/$integrationId" `
            --profile $profile `
            --region $region | Out-Null
        Write-Host "  Updated route: $($route.RouteKey)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Integration updated!" -ForegroundColor Green
Write-Host ""

# Grant API Gateway permission to invoke Lambda
Write-Host "Granting API Gateway permission to invoke Lambda..." -ForegroundColor Yellow
$accountId = aws sts get-caller-identity --profile $profile --region $region --query 'Account' --output text
$statementId = "apigateway-invoke-$(Get-Date -Format 'yyyyMMddHHmmss')"
$sourceArn = "arn:aws:execute-api:${region}:${accountId}:${apiId}/*/*"
try {
    aws lambda add-permission `
        --function-name $lambdaName `
        --statement-id $statementId `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn $sourceArn `
        --profile $profile `
        --region $region 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "  Permission granted!" -ForegroundColor Green }
    else { Write-Host "  Permission may already exist (this is OK)" -ForegroundColor Yellow }
} catch {
    Write-Host "  Permission may already exist (this is OK)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "API Gateway Update Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "API Endpoint: https://${apiId}.execute-api.${region}.amazonaws.com/production/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test with:" -ForegroundColor Yellow
Write-Host "  curl https://${apiId}.execute-api.${region}.amazonaws.com/production/health" -ForegroundColor White
