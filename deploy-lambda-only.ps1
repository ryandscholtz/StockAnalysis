#!/usr/bin/env pwsh

Write-Host "Deploying Lambda Function with Watchlist Support (Cerebrum Profile)" -ForegroundColor Green

# Set AWS profile to Cerebrum
$env:AWS_PROFILE = "Cerebrum"
Write-Host "Using AWS Profile: Cerebrum" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "backend")) {
    Write-Host "Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "Creating Lambda deployment package..." -ForegroundColor Yellow

# Navigate to backend
Set-Location backend

# Remove old dist files
if (Test-Path "dist") {
    Remove-Item "dist" -Recurse -Force
}

# Create dist directory
New-Item -ItemType Directory -Path "dist" -Force | Out-Null

# Copy application files
Write-Host "Copying application files..." -ForegroundColor White
Copy-Item -Path "app" -Destination "dist/app" -Recurse -Force
Copy-Item -Path "lambda_handler.py" -Destination "dist/" -Force

# Create a simple requirements.txt for Lambda
Write-Host "Creating requirements for Lambda..." -ForegroundColor White
$lambdaRequirements = @"
fastapi==0.104.1
mangum==0.17.0
pydantic==2.5.0
sqlalchemy==2.0.23
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
requests==2.31.0
boto3==1.34.0
botocore==1.34.0
"@

$lambdaRequirements | Out-File -FilePath "dist/requirements.txt" -Encoding UTF8

# Install dependencies in dist directory
Write-Host "Installing Python dependencies..." -ForegroundColor White
Set-Location dist

# Install all dependencies with their sub-dependencies
pip install fastapi==0.104.1 -t . --quiet
pip install mangum==0.17.0 -t . --quiet
pip install pydantic==2.5.0 -t . --quiet
pip install sqlalchemy==2.0.23 -t . --quiet
pip install python-multipart==0.0.6 -t . --quiet
pip install requests==2.31.0 -t . --quiet
pip install python-dotenv==1.0.0 -t . --quiet
pip install python-jose[cryptography]==3.3.0 -t . --quiet
pip install passlib[bcrypt]==1.7.4 -t . --quiet

Write-Host "Creating deployment zip..." -ForegroundColor White
Compress-Archive -Path * -DestinationPath ../lambda-deployment.zip -Force

Set-Location ..

# Update Lambda function
Write-Host "Updating Lambda function..." -ForegroundColor Green

$FunctionName = "stock-analysis-api-production"
$ZipFile = "lambda-deployment.zip"

try {
    Write-Host "Uploading new code to Lambda (using Cerebrum profile)..." -ForegroundColor Yellow
    aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile" --profile Cerebrum --region eu-west-1 --output table
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Lambda function updated successfully!" -ForegroundColor Green
        
        # Update handler to use the correct module name
        Write-Host "Updating Lambda handler..." -ForegroundColor Yellow
        aws lambda update-function-configuration --function-name $FunctionName --handler simple_marketstack_lambda.lambda_handler --profile Cerebrum --region eu-west-1 --output table
        
        # Wait for function to be ready
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 15
        
        # Test the endpoint
        Write-Host "Testing watchlist endpoint..." -ForegroundColor Yellow
        
        try {
            $response = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist" -Method GET -TimeoutSec 30
            Write-Host "Watchlist endpoint is working!" -ForegroundColor Green
            Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Cyan
        } catch {
            Write-Host "Testing endpoint..." -ForegroundColor Yellow
            Write-Host "If you see a 404, the endpoint might need a few more seconds to be ready." -ForegroundColor Yellow
            
            # Test health endpoint to verify deployment
            try {
                $healthResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" -Method GET -TimeoutSec 30
                Write-Host "Health check response: $($healthResponse | ConvertTo-Json -Compress)" -ForegroundColor Cyan
                
                if ($healthResponse.version -eq "2.0.0") {
                    Write-Host "Deployment successful! New version 2.0.0 is active." -ForegroundColor Green
                } else {
                    Write-Host "Warning: Still showing old version. May need more time to propagate." -ForegroundColor Yellow
                }
            } catch {
                Write-Host "Could not test health endpoint: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
        
    } else {
        Write-Host "Lambda update failed!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error updating Lambda function: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor White
Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "lambda-deployment.zip" -Force -ErrorAction SilentlyContinue

Set-Location ..

Write-Host "Lambda deployment complete!" -ForegroundColor Green
Write-Host "The watchlist endpoint should now be available at:" -ForegroundColor Cyan
Write-Host "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist" -ForegroundColor Cyan