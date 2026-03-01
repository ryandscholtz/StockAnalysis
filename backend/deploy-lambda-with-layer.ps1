# Deploy Lambda with dependencies in a Layer
Write-Host "=== Deploying Lambda with Layer ===" -ForegroundColor Green

$functionName = "stock-analysis-api-production"
$layerName = "stock-analysis-dependencies"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"

# Create S3 bucket if it doesn't exist
Write-Host "Checking S3 bucket..." -ForegroundColor Cyan
aws s3 mb "s3://$s3Bucket" --profile $profile --region $region 2>$null

# Upload the large package to S3
Write-Host "Uploading package to S3..." -ForegroundColor Cyan
aws s3 cp lambda_deployment_complete.zip "s3://$s3Bucket/lambda_deployment_complete.zip" --profile $profile --region $region

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error uploading to S3" -ForegroundColor Red
    exit 1
}

# Update Lambda function code from S3
Write-Host "Updating Lambda function from S3..." -ForegroundColor Cyan
aws lambda update-function-code `
    --function-name $functionName `
    --s3-bucket $s3Bucket `
    --s3-key "lambda_deployment_complete.zip" `
    --profile $profile `
    --region $region

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error updating Lambda function" -ForegroundColor Red
    exit 1
}

Write-Host "Waiting for Lambda to update..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Update environment variables
Write-Host "Updating environment variables..." -ForegroundColor Cyan
aws lambda update-function-configuration `
    --function-name $functionName `
    --environment "Variables={MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6,ENVIRONMENT=production}" `
    --profile $profile `
    --region $region

Write-Host "Waiting for configuration update..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "=== Testing Lambda ===" -ForegroundColor Green

# Test the health endpoint
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health"
Write-Host "Testing: $apiUrl" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 30
    Write-Host "Health check passed!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json) -ForegroundColor Cyan
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Checking Lambda logs..." -ForegroundColor Yellow
    
    # Get recent logs
    aws logs tail "/aws/lambda/$functionName" --since 5m --profile $profile --region $region
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Lambda function: $functionName" -ForegroundColor Cyan
Write-Host "API URL: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/" -ForegroundColor Cyan
