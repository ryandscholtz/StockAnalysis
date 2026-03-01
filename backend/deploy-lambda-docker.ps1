# Deploy Lambda as Docker Container Image
# This solves the 250MB unzipped limit by using container images (up to 10GB)

param(
    [string]$FunctionName = "stock-analysis-api-production",
    [string]$Profile = "Cerebrum",
    [string]$Region = "eu-west-1",
    [string]$RepositoryName = "stock-analysis-api"
)

Write-Host "=== Deploying Lambda as Docker Container ===" -ForegroundColor Green
Write-Host "Function: $FunctionName" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host "Repository: $RepositoryName" -ForegroundColor Cyan
Write-Host ""

# Get AWS account ID
Write-Host "Getting AWS account ID..." -ForegroundColor Cyan
$accountId = aws sts get-caller-identity --profile $Profile --query Account --output text
if (-not $accountId) {
    Write-Host "Failed to get AWS account ID. Check your AWS credentials." -ForegroundColor Red
    exit 1
}
Write-Host "Account ID: $accountId" -ForegroundColor Green

# ECR repository URI
$ecrUri = "$accountId.dkr.ecr.$Region.amazonaws.com/$RepositoryName"
Write-Host "ECR URI: $ecrUri" -ForegroundColor Cyan
Write-Host ""

# Check if ECR repository exists, create if not
Write-Host "Checking ECR repository..." -ForegroundColor Cyan
$repoExists = aws ecr describe-repositories --repository-names $RepositoryName --profile $Profile --region $Region 2>$null
if (-not $repoExists) {
    Write-Host "Creating ECR repository..." -ForegroundColor Yellow
    aws ecr create-repository `
        --repository-name $RepositoryName `
        --profile $Profile `
        --region $Region `
        --image-scanning-configuration scanOnPush=true `
        --image-tag-mutability MUTABLE | Out-Null
    Write-Host "Repository created" -ForegroundColor Green
} else {
    Write-Host "Repository exists" -ForegroundColor Green
}

# Login to ECR
Write-Host "Logging in to ECR..." -ForegroundColor Cyan
$loginCmd = aws ecr get-login-password --profile $Profile --region $Region | docker login --username AWS --password-stdin $ecrUri
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to login to ECR" -ForegroundColor Red
    exit 1
}
Write-Host "Logged in successfully" -ForegroundColor Green

# Build Docker image
Write-Host ""
Write-Host "Building Docker image..." -ForegroundColor Cyan
$imageTag = "latest"
$imageUri = "$ecrUri`:$imageTag"

docker build -f Dockerfile.lambda -t $RepositoryName`:$imageTag .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed" -ForegroundColor Red
    exit 1
}
Write-Host "Image built successfully" -ForegroundColor Green

# Tag image for ECR
Write-Host "Tagging image for ECR..." -ForegroundColor Cyan
docker tag $RepositoryName`:$imageTag $imageUri
Write-Host "Image tagged" -ForegroundColor Green

# Push image to ECR
Write-Host "Pushing image to ECR..." -ForegroundColor Cyan
docker push $imageUri
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to push image to ECR" -ForegroundColor Red
    exit 1
}
Write-Host "Image pushed successfully" -ForegroundColor Green

# Update Lambda function to use container image
Write-Host ""
Write-Host "Updating Lambda function..." -ForegroundColor Cyan
aws lambda update-function-code `
    --function-name $FunctionName `
    --image-uri $imageUri `
    --profile $Profile `
    --region $Region | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to update Lambda function" -ForegroundColor Red
    exit 1
}
Write-Host "Lambda function updated" -ForegroundColor Green

# Wait for update to complete
Write-Host "Waiting for Lambda update to complete..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# Update environment variables if needed
Write-Host "Updating environment variables..." -ForegroundColor Cyan
aws lambda update-function-configuration `
    --function-name $FunctionName `
    --environment "Variables={MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6,ENVIRONMENT=production}" `
    --profile $Profile `
    --region $Region | Out-Null

Write-Host "Configuration updated" -ForegroundColor Green

# Wait for configuration update
Write-Host "Waiting for configuration update..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Test deployment
Write-Host ""
Write-Host "Testing deployment..." -ForegroundColor Cyan
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health"

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 60
    Write-Host ""
    Write-Host "[SUCCESS] Health check PASSED!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 3) -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "[WARNING] Health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "This might be a cold start (can take 10-30 seconds for container images)" -ForegroundColor Yellow
    Write-Host "Checking logs..." -ForegroundColor Yellow
    aws logs tail "/aws/lambda/$FunctionName" --since 2m --profile $Profile --region $Region --format short
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Lambda function is now using container image" -ForegroundColor Cyan
Write-Host "Image URI: $imageUri" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Container images have slower cold starts (5-10 seconds)" -ForegroundColor Yellow
Write-Host "but allow unlimited package size (up to 10GB)" -ForegroundColor Yellow
