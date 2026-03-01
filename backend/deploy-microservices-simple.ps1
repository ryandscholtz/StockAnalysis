# Simple Microservices Deployment Script
# Uses existing IAM role and simplified deployment
# AWS profile: Cerebrum (set so CLI uses it for all commands)

$ErrorActionPreference = "Stop"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"
$roleArn = "arn:aws:iam::295202642810:role/StockAnalysisInfrastructu-LambdaExecutionRoleD5C260-kW9wvngtVo2R"

# Ensure AWS CLI uses Cerebrum profile for this session
$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stock Analysis Microservices Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Profile: $profile | Region: $region" -ForegroundColor Gray
Write-Host ""

# Function to create and deploy Lambda
function Deploy-SimpleLambda {
    param(
        [string]$Name,
        [string]$FunctionName,
        [string]$Handler,
        [string]$Requirements,
        [int]$Memory = 512,
        [int]$Timeout = 30
    )
    
    Write-Host "Deploying $Name..." -ForegroundColor Yellow
    
    # Create temp directory
    $tempDir = "lambda_temp_$Name"
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    # Install dependencies if requirements file exists
    if (Test-Path $Requirements) {
        $reqContent = Get-Content $Requirements
        # Skip if only boto3 (already in Lambda runtime)
        if ($reqContent -match "^boto3" -and $reqContent.Count -eq 1) {
            Write-Host "  Skipping dependencies (boto3 included in Lambda runtime)" -ForegroundColor Gray
        } else {
            Write-Host "  Installing dependencies..." -ForegroundColor Gray
            try {
                pip install -r $Requirements -t $tempDir --platform manylinux2014_x86_64 --only-binary=:all: --upgrade 2>&1 | Out-Null
            } catch {
                Write-Host "  Warning: Some dependencies may have failed to install" -ForegroundColor Yellow
            }
        }
    }
    
    # Copy handler file
    Copy-Item $Handler -Destination "$tempDir/lambda_function.py"
    
    # Create zip
    $zipFile = "$Name.zip"
    Write-Host "  Creating package..." -ForegroundColor Gray
    
    Push-Location $tempDir
    if (Test-Path "../$zipFile") {
        Remove-Item "../$zipFile"
    }
    
    Compress-Archive -Path * -DestinationPath "../$zipFile" -CompressionLevel Fastest
    Pop-Location
    
    # Clean up temp directory
    Remove-Item -Recurse -Force $tempDir
    
    $size = (Get-Item $zipFile).Length / 1MB
    Write-Host "  Package size: $([math]::Round($size, 2)) MB" -ForegroundColor Gray
    
    # Upload to S3
    Write-Host "  Uploading to S3..." -ForegroundColor Gray
    $s3Key = "microservices/$zipFile"
    aws s3 cp $zipFile "s3://$s3Bucket/$s3Key" --profile $profile --region $region --quiet
    
    # Check if Lambda exists
    $ErrorActionPreference = "SilentlyContinue"
    $exists = aws lambda get-function --function-name $FunctionName --profile $profile --region $region 2>&1
    $lambdaExists = $LASTEXITCODE -eq 0
    $ErrorActionPreference = "Stop"
    
    if ($lambdaExists) {
        # Update existing Lambda
        Write-Host "  Updating Lambda function..." -ForegroundColor Gray
        aws lambda update-function-code `
            --function-name $FunctionName `
            --s3-bucket $s3Bucket `
            --s3-key $s3Key `
            --profile $profile `
            --region $region | Out-Null
        
        Start-Sleep -Seconds 2
        
        aws lambda update-function-configuration `
            --function-name $FunctionName `
            --memory-size $Memory `
            --timeout $Timeout `
            --profile $profile `
            --region $region | Out-Null
    } else {
        # Create new Lambda
        Write-Host "  Creating Lambda function..." -ForegroundColor Gray
        aws lambda create-function `
            --function-name $FunctionName `
            --runtime python3.11 `
            --role $roleArn `
            --handler lambda_function.lambda_handler `
            --code S3Bucket=$s3Bucket,S3Key=$s3Key `
            --memory-size $Memory `
            --timeout $Timeout `
            --profile $profile `
            --region $region | Out-Null
    }
    
    Write-Host "  $Name deployed!" -ForegroundColor Green
    Write-Host ""
}

# Change to backend directory
Push-Location $PSScriptRoot

try {
    # 1. Deploy Auth/Watchlist Lambda (smallest, fastest)
    Deploy-SimpleLambda `
        -Name "lambda-auth" `
        -FunctionName "stock-analysis-auth" `
        -Handler "lambda_auth_watchlist.py" `
        -Requirements "requirements-auth.txt" `
        -Memory 256 `
        -Timeout 15
    
    # 2. Deploy Analysis Lambda
    Deploy-SimpleLambda `
        -Name "lambda-analysis" `
        -FunctionName "stock-analysis-analyzer" `
        -Handler "lambda_analysis.py" `
        -Requirements "requirements-analysis.txt" `
        -Memory 512 `
        -Timeout 60
    
    # 3. Deploy PDF Processing Lambda
    Deploy-SimpleLambda `
        -Name "lambda-pdf" `
        -FunctionName "stock-analysis-pdf-processor" `
        -Handler "lambda_pdf_processor.py" `
        -Requirements "requirements-pdf.txt" `
        -Memory 1024 `
        -Timeout 60
    
    # 4. Deploy Stock Data Lambda
    Deploy-SimpleLambda `
        -Name "lambda-stock-data" `
        -FunctionName "stock-analysis-stock-data" `
        -Handler "lambda_stock_data.py" `
        -Requirements "requirements-stock-data.txt" `
        -Memory 512 `
        -Timeout 30
    
    # 5. Deploy API Gateway Lambda (Router)
    Deploy-SimpleLambda `
        -Name "lambda-gateway" `
        -FunctionName "stock-analysis-gateway" `
        -Handler "api_gateway_lambda.py" `
        -Requirements "requirements-gateway.txt" `
        -Memory 256 `
        -Timeout 30
    
    # Configure Gateway Lambda environment variables
    Write-Host "Configuring API Gateway Lambda..." -ForegroundColor Yellow
    aws lambda update-function-configuration `
        --function-name stock-analysis-gateway `
        --environment "Variables={STOCK_DATA_LAMBDA=stock-analysis-stock-data,PDF_LAMBDA=stock-analysis-pdf-processor,ANALYSIS_LAMBDA=stock-analysis-analyzer,AUTH_LAMBDA=stock-analysis-auth,MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6,CORS_ALLOW_ALL=true}" `
        --profile $profile `
        --region $region | Out-Null
    
    Write-Host "  Environment variables configured!" -ForegroundColor Green
    Write-Host ""
    
    # Update API Gateway to use new Lambda
    Write-Host "Updating API Gateway..." -ForegroundColor Yellow
    Write-Host "  Note: You may need to manually update API Gateway integration" -ForegroundColor Gray
    Write-Host "  API ID: dx0w31lbc1" -ForegroundColor Gray
    Write-Host "  New Lambda: stock-analysis-gateway" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Deployment Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Deployed Functions:" -ForegroundColor Cyan
    Write-Host "  1. stock-analysis-auth (Auth & Watchlist)" -ForegroundColor White
    Write-Host "  2. stock-analysis-analyzer (Analysis)" -ForegroundColor White
    Write-Host "  3. stock-analysis-pdf-processor (PDF Processing)" -ForegroundColor White
    Write-Host "  4. stock-analysis-stock-data (Stock Data)" -ForegroundColor White
    Write-Host "  5. stock-analysis-gateway (API Router)" -ForegroundColor White
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Update API Gateway to use 'stock-analysis-gateway' Lambda" -ForegroundColor White
    Write-Host "  2. Test the API endpoint" -ForegroundColor White
    Write-Host ""
    Write-Host "API Endpoint: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/" -ForegroundColor Cyan
    
} finally {
    Pop-Location
}
