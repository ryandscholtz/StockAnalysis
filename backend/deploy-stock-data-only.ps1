# Deploy only the Stock Data Lambda (with yfinance + explore endpoints)
# Uses AWS profile: Cerebrum, region: eu-west-1

$ErrorActionPreference = "Stop"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"
$functionName = "stock-analysis-stock-data"

$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploy Stock Data Lambda only" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Profile: $profile | Region: $region" -ForegroundColor Gray
Write-Host ""

Push-Location $PSScriptRoot

try {
    $name = "lambda-stock-data"
    $tempDir = "lambda_temp_$name"
    if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
    New-Item -ItemType Directory -Path $tempDir | Out-Null

    Write-Host "Installing yfinance dependencies (cp311 manylinux)..." -ForegroundColor Gray
    pip install yfinance==0.2.28 requests pandas==2.1.3 numpy==1.26.2 `
        -t $tempDir `
        --platform manylinux2014_x86_64 `
        --implementation cp `
        --python-version 311 `
        --only-binary=:all: `
        --upgrade -q

    Write-Host "Copying handler..." -ForegroundColor Gray
    Copy-Item "lambda_stock_data.py" -Destination "$tempDir/lambda_function.py"

    $zipFile = "$name.zip"
    if (Test-Path $zipFile) { Remove-Item $zipFile }
    Push-Location $tempDir
    Compress-Archive -Path * -DestinationPath "..\$zipFile" -CompressionLevel Fastest
    Pop-Location
    Remove-Item -Recurse -Force $tempDir

    $sizeMB = [math]::Round((Get-Item $zipFile).Length / 1MB, 1)
    Write-Host "Package size: $sizeMB MB" -ForegroundColor Gray

    $s3Key = "microservices/$zipFile"
    Write-Host "Uploading to S3..." -ForegroundColor Yellow
    aws s3 cp $zipFile "s3://$s3Bucket/$s3Key" --profile $profile --region $region --quiet

    Write-Host "Updating Lambda code..." -ForegroundColor Yellow
    aws lambda update-function-code `
        --function-name $functionName `
        --s3-bucket $s3Bucket `
        --s3-key $s3Key `
        --profile $profile `
        --region $region | Out-Null

    Write-Host "Waiting for update to complete..." -ForegroundColor Gray
    Start-Sleep -Seconds 8

    aws lambda update-function-configuration `
        --function-name $functionName `
        --timeout 300 `
        --memory-size 512 `
        --profile $profile `
        --region $region | Out-Null

    Remove-Item $zipFile

    Write-Host ""
    Write-Host "Done. Stock Data Lambda ($functionName) updated." -ForegroundColor Green
    Write-Host "GET /api/explore/markets and /api/explore/stocks now work." -ForegroundColor Gray
}
finally {
    Pop-Location
}
