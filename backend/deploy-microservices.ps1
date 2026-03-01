# Deploy Stock Analysis Microservices Architecture
# This script deploys 5 specialized Lambda functions

$ErrorActionPreference = "Stop"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stock Analysis Microservices Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to create Lambda package
function Create-LambdaPackage {
    param(
        [string]$Name,
        [string]$Handler,
        [string]$Requirements
    )
    
    Write-Host "Creating package for $Name..." -ForegroundColor Yellow
    
    # Create temp directory
    $tempDir = "lambda_build_$Name"
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    # Install dependencies if requirements file exists
    if (Test-Path $Requirements) {
        Write-Host "  Installing dependencies from $Requirements..." -ForegroundColor Gray
        pip install -r $Requirements -t $tempDir --platform manylinux2014_x86_64 --only-binary=:all: --upgrade --quiet
    }
    
    # Copy handler file
    Write-Host "  Copying handler file..." -ForegroundColor Gray
    Copy-Item $Handler -Destination "$tempDir/lambda_function.py"
    
    # Create zip
    $zipFile = "$Name.zip"
    Write-Host "  Creating zip file..." -ForegroundColor Gray
    
    Push-Location $tempDir
    if (Test-Path "../$zipFile") {
        Remove-Item "../$zipFile"
    }
    
    # Use Python to create zip (more reliable on Windows)
    python -c "import shutil; shutil.make_archive('../$Name', 'zip', '.')"
    Pop-Location
    
    # Clean up temp directory
    Remove-Item -Recurse -Force $tempDir
    
    $size = (Get-Item $zipFile).Length / 1MB
    Write-Host "  Package created: $zipFile ($([math]::Round($size, 2)) MB)" -ForegroundColor Green
    
    return $zipFile
}

# Function to deploy Lambda
function Deploy-Lambda {
    param(
        [string]$FunctionName,
        [string]$ZipFile,
        [string]$Description,
        [int]$Memory = 512,
        [int]$Timeout = 30
    )
    
    Write-Host ""
    Write-Host "Deploying $FunctionName..." -ForegroundColor Yellow
    
    # Upload to S3
    $s3Key = "microservices/$ZipFile"
    Write-Host "  Uploading to S3..." -ForegroundColor Gray
    aws s3 cp $ZipFile "s3://$s3Bucket/$s3Key" --profile $profile --region $region
    
    # Check if Lambda exists
    $ErrorActionPreference = "SilentlyContinue"
    $exists = aws lambda get-function --function-name $FunctionName --profile $profile --region $region 2>&1
    $ErrorActionPreference = "Stop"
    
    if ($LASTEXITCODE -eq 0) {
        # Update existing Lambda
        Write-Host "  Updating existing Lambda function..." -ForegroundColor Gray
        aws lambda update-function-code `
            --function-name $FunctionName `
            --s3-bucket $s3Bucket `
            --s3-key $s3Key `
            --profile $profile `
            --region $region | Out-Null
        
        Write-Host "  Updating configuration..." -ForegroundColor Gray
        aws lambda update-function-configuration `
            --function-name $FunctionName `
            --memory-size $Memory `
            --timeout $Timeout `
            --description $Description `
            --profile $profile `
            --region $region | Out-Null
    } else {
        # Create new Lambda
        Write-Host "  Creating new Lambda function..." -ForegroundColor Gray
        
        # Get execution role ARN
        $ErrorActionPreference = "SilentlyContinue"
        $roleArn = aws iam get-role --role-name lambda-execution-role --profile $profile --query 'Role.Arn' --output text 2>&1
        $roleExists = $LASTEXITCODE -eq 0
        $ErrorActionPreference = "Stop"
        
        if (-not $roleExists) {
            Write-Host "  Error: Lambda execution role not found. Creating role..." -ForegroundColor Red
            
            # Create trust policy
            $trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@
            $trustPolicy | Out-File -FilePath "trust-policy.json" -Encoding utf8
            
            aws iam create-role `
                --role-name lambda-execution-role `
                --assume-role-policy-document file://trust-policy.json `
                --profile $profile | Out-Null
            
            aws iam attach-role-policy `
                --role-name lambda-execution-role `
                --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" `
                --profile $profile
            
            aws iam attach-role-policy `
                --role-name lambda-execution-role `
                --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess" `
                --profile $profile
            
            aws iam attach-role-policy `
                --role-name lambda-execution-role `
                --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" `
                --profile $profile
            
            aws iam attach-role-policy `
                --role-name lambda-execution-role `
                --policy-arn "arn:aws:iam::aws:policy/AWSLambda_FullAccess" `
                --profile $profile
            
            Remove-Item "trust-policy.json"
            
            # Wait for role to be available
            Write-Host "  Waiting for IAM role to be available..." -ForegroundColor Gray
            Start-Sleep -Seconds 10
            
            $roleArn = aws iam get-role --role-name lambda-execution-role --profile $profile --query 'Role.Arn' --output text
        }
        
        aws lambda create-function `
            --function-name $FunctionName `
            --runtime python3.11 `
            --role $roleArn `
            --handler lambda_function.lambda_handler `
            --code S3Bucket=$s3Bucket,S3Key=$s3Key `
            --memory-size $Memory `
            --timeout $Timeout `
            --description $Description `
            --profile $profile `
            --region $region | Out-Null
    }
    
    Write-Host "  $FunctionName deployed successfully!" -ForegroundColor Green
}

# Change to backend directory
Push-Location $PSScriptRoot

try {
    # 1. Deploy API Gateway Lambda (Router)
    Write-Host ""
    Write-Host "1/5 Deploying API Gateway Lambda..." -ForegroundColor Cyan
    $gatewayZip = Create-LambdaPackage -Name "lambda-gateway" -Handler "api_gateway_lambda.py" -Requirements "requirements-gateway.txt"
    Deploy-Lambda -FunctionName "stock-analysis-gateway" -ZipFile $gatewayZip -Description "API Gateway router for microservices" -Memory 256 -Timeout 30
    
    # 2. Deploy Auth/Watchlist Lambda
    Write-Host ""
    Write-Host "2/5 Deploying Auth & Watchlist Lambda..." -ForegroundColor Cyan
    $authZip = Create-LambdaPackage -Name "lambda-auth" -Handler "lambda_auth_watchlist.py" -Requirements "requirements-auth.txt"
    Deploy-Lambda -FunctionName "stock-analysis-auth" -ZipFile $authZip -Description "Authentication and watchlist management" -Memory 256 -Timeout 15
    
    # 3. Deploy Analysis Lambda
    Write-Host ""
    Write-Host "3/5 Deploying Analysis Lambda..." -ForegroundColor Cyan
    $analysisZip = Create-LambdaPackage -Name "lambda-analysis" -Handler "lambda_analysis.py" -Requirements "requirements-analysis.txt"
    Deploy-Lambda -FunctionName "stock-analysis-analyzer" -ZipFile $analysisZip -Description "Stock analysis and valuation calculations" -Memory 512 -Timeout 60
    
    # 4. Deploy PDF Processing Lambda
    Write-Host ""
    Write-Host "4/5 Deploying PDF Processing Lambda..." -ForegroundColor Cyan
    $pdfZip = Create-LambdaPackage -Name "lambda-pdf" -Handler "lambda_pdf_processor.py" -Requirements "requirements-pdf.txt"
    Deploy-Lambda -FunctionName "stock-analysis-pdf-processor" -ZipFile $pdfZip -Description "PDF upload and text extraction" -Memory 1024 -Timeout 60
    
    # 5. Deploy Stock Data Lambda
    Write-Host ""
    Write-Host "5/5 Deploying Stock Data Lambda..." -ForegroundColor Cyan
    $stockZip = Create-LambdaPackage -Name "lambda-stock-data" -Handler "lambda_stock_data.py" -Requirements "requirements-stock-data.txt"
    Deploy-Lambda -FunctionName "stock-analysis-stock-data" -ZipFile $stockZip -Description "Stock price data and market information" -Memory 512 -Timeout 30
    
    # Update API Gateway Lambda environment variables with function names
    Write-Host ""
    Write-Host "Configuring API Gateway Lambda..." -ForegroundColor Yellow
    aws lambda update-function-configuration `
        --function-name stock-analysis-gateway `
        --environment "Variables={STOCK_DATA_LAMBDA=stock-analysis-stock-data,PDF_LAMBDA=stock-analysis-pdf-processor,ANALYSIS_LAMBDA=stock-analysis-analyzer,AUTH_LAMBDA=stock-analysis-auth,MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6,CORS_ALLOW_ALL=true}" `
        --profile $profile `
        --region $region | Out-Null
    
    Write-Host "  Environment variables configured!" -ForegroundColor Green
    
    # Update API Gateway to point to new Lambda
    Write-Host ""
    Write-Host "Updating API Gateway integration..." -ForegroundColor Yellow
    
    # Get API Gateway ID
    $apiId = "dx0w31lbc1"
    
    # Update integration to use gateway Lambda
    aws apigatewayv2 update-integration `
        --api-id $apiId `
        --integration-id (aws apigatewayv2 get-integrations --api-id $apiId --profile $profile --region $region --query 'Items[0].IntegrationId' --output text) `
        --integration-uri "arn:aws:lambda:${region}:$(aws sts get-caller-identity --profile $profile --query 'Account' --output text):function:stock-analysis-gateway" `
        --profile $profile `
        --region $region 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  API Gateway updated successfully!" -ForegroundColor Green
    } else {
        Write-Host "  Note: API Gateway update may need manual configuration" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Deployment Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Deployed Functions:" -ForegroundColor Cyan
    Write-Host "  1. stock-analysis-gateway (API Router)" -ForegroundColor White
    Write-Host "  2. stock-analysis-auth (Auth & Watchlist)" -ForegroundColor White
    Write-Host "  3. stock-analysis-analyzer (Analysis)" -ForegroundColor White
    Write-Host "  4. stock-analysis-pdf-processor (PDF Processing)" -ForegroundColor White
    Write-Host "  5. stock-analysis-stock-data (Stock Data)" -ForegroundColor White
    Write-Host ""
    Write-Host "API Endpoint: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Testing the API..." -ForegroundColor Yellow
    
    # Test health endpoint
    $response = Invoke-WebRequest -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" -Method GET -UseBasicParsing 2>&1
    
    if ($response.StatusCode -eq 200) {
        Write-Host "  Health check: PASSED" -ForegroundColor Green
    } else {
        Write-Host "  Health check: FAILED (may need a few seconds to warm up)" -ForegroundColor Yellow
    }
    
} finally {
    Pop-Location
}
