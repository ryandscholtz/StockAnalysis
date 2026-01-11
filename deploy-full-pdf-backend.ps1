#!/usr/bin/env pwsh

Write-Host "Deploying Full FastAPI Backend with PDF Processing (Cerebrum Profile)" -ForegroundColor Green

# Set AWS profile to Cerebrum
$env:AWS_PROFILE = "Cerebrum"
Write-Host "Using AWS Profile: Cerebrum" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "backend")) {
    Write-Host "Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "Creating Lambda deployment package with PDF processing..." -ForegroundColor Yellow

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
Copy-Item -Path "enhanced_textract_extractor.py" -Destination "dist/" -Force

# Create enhanced requirements for Lambda with PDF processing
Write-Host "Creating requirements for Lambda with PDF processing..." -ForegroundColor White
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
yfinance==0.2.28
pandas==2.1.3
numpy==1.26.2
httpx==0.25.2
beautifulsoup4==4.12.2
PyJWT==2.8.0
PyMuPDF>=1.23.0
Pillow>=9.0.0
"@

$lambdaRequirements | Out-File -FilePath "dist/requirements.txt" -Encoding UTF8

# Install dependencies in dist directory
Write-Host "Installing Python dependencies (this may take a few minutes)..." -ForegroundColor White
Set-Location dist

# Install core FastAPI dependencies
Write-Host "Installing FastAPI and core dependencies..." -ForegroundColor Cyan
pip install fastapi==0.104.1 -t . --quiet
pip install mangum==0.17.0 -t . --quiet
pip install pydantic==2.5.0 -t . --quiet
pip install sqlalchemy==2.0.23 -t . --quiet
pip install python-multipart==0.0.6 -t . --quiet
pip install requests==2.31.0 -t . --quiet
pip install python-dotenv==1.0.0 -t . --quiet
pip install python-jose[cryptography]==3.3.0 -t . --quiet
pip install passlib[bcrypt]==1.7.4 -t . --quiet

# Install AWS and data processing dependencies
Write-Host "Installing AWS and data processing dependencies..." -ForegroundColor Cyan
pip install boto3==1.34.0 -t . --quiet
pip install yfinance==0.2.28 -t . --quiet
pip install pandas==2.1.3 -t . --quiet
pip install numpy==1.26.2 -t . --quiet
pip install httpx==0.25.2 -t . --quiet
pip install beautifulsoup4==4.12.2 -t . --quiet
pip install PyJWT==2.8.0 -t . --quiet

# Install PDF processing dependencies
Write-Host "Installing PDF processing dependencies..." -ForegroundColor Cyan
pip install PyMuPDF>=1.23.0 -t . --quiet
pip install Pillow>=9.0.0 -t . --quiet

Write-Host "Creating deployment zip..." -ForegroundColor White
Compress-Archive -Path * -DestinationPath ../lambda-full-pdf.zip -Force

Set-Location ..

# Update Lambda function
Write-Host "Updating Lambda function with full PDF processing..." -ForegroundColor Green

$FunctionName = "stock-analysis-api-production"
$ZipFile = "lambda-full-pdf.zip"

try {
    Write-Host "Uploading new code to Lambda (using Cerebrum profile)..." -ForegroundColor Yellow
    aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile" --profile Cerebrum --region eu-west-1 --output table
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Lambda function updated successfully!" -ForegroundColor Green
        
        # Update handler to use the FastAPI backend
        Write-Host "Updating Lambda handler to use FastAPI backend..." -ForegroundColor Yellow
        aws lambda update-function-configuration --function-name $FunctionName --handler lambda_handler.lambda_handler --profile Cerebrum --region eu-west-1 --output table
        
        # Increase timeout for PDF processing
        Write-Host "Increasing timeout for PDF processing..." -ForegroundColor Yellow
        aws lambda update-function-configuration --function-name $FunctionName --timeout 900 --profile Cerebrum --region eu-west-1 --output table
        
        # Wait for function to be ready
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
        
        # Test the health endpoint
        Write-Host "Testing health endpoint..." -ForegroundColor Yellow
        
        try {
            $healthResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" -Method GET -TimeoutSec 30
            Write-Host "Health check response: $($healthResponse | ConvertTo-Json -Compress)" -ForegroundColor Cyan
            
            # Test the version endpoint
            Write-Host "Testing version endpoint..." -ForegroundColor Yellow
            $versionResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/version" -Method GET -TimeoutSec 30
            Write-Host "Version response: $($versionResponse | ConvertTo-Json -Compress)" -ForegroundColor Cyan
            
            # Test the watchlist endpoint
            Write-Host "Testing watchlist endpoint..." -ForegroundColor Yellow
            $watchlistResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist" -Method GET -TimeoutSec 30
            Write-Host "Watchlist endpoint is working!" -ForegroundColor Green
            
            Write-Host "Full FastAPI backend with PDF processing deployed successfully!" -ForegroundColor Green
            
        } catch {
            Write-Host "Warning: Some endpoints may not be ready yet. Error: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "This is normal for the first deployment. The function may need a few more minutes to be fully ready." -ForegroundColor Yellow
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
Remove-Item "lambda-full-pdf.zip" -Force -ErrorAction SilentlyContinue

Set-Location ..

Write-Host "Full FastAPI backend deployment complete!" -ForegroundColor Green
Write-Host "Available endpoints:" -ForegroundColor Cyan
Write-Host "- Health: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" -ForegroundColor Cyan
Write-Host "- Watchlist: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist" -ForegroundColor Cyan
Write-Host "- PDF Upload: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/upload-pdf" -ForegroundColor Cyan
Write-Host "- Analysis: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/{ticker}" -ForegroundColor Cyan

Write-Host "" -ForegroundColor White
Write-Host "PDF Processing Features:" -ForegroundColor Green
Write-Host "✅ AWS Textract integration for direct PDF text extraction" -ForegroundColor White
Write-Host "✅ OCR fallback for scanned/image-based PDFs" -ForegroundColor White
Write-Host "✅ Financial data extraction using LLM" -ForegroundColor White
Write-Host "✅ Support for complex financial statements" -ForegroundColor White