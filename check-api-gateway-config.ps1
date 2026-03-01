# Check API Gateway Configuration
$ErrorActionPreference = "Continue"
$profile = "Cerebrum"
$region = "eu-west-1"
$apiId = "dx0w31lbc1"

Write-Host "Checking API Gateway Configuration..." -ForegroundColor Cyan
Write-Host ""

# Get API details
Write-Host "API Details:" -ForegroundColor Yellow
aws apigatewayv2 get-api --api-id $apiId --profile $profile --region $region 2>&1

Write-Host ""
Write-Host "Routes:" -ForegroundColor Yellow
aws apigatewayv2 get-routes --api-id $apiId --profile $profile --region $region 2>&1

Write-Host ""
Write-Host "Integrations:" -ForegroundColor Yellow
aws apigatewayv2 get-integrations --api-id $apiId --profile $profile --region $region 2>&1

Write-Host ""
Write-Host "Stages:" -ForegroundColor Yellow
aws apigatewayv2 get-stages --api-id $apiId --profile $profile --region $region 2>&1
