# Deploy only the Auth/Watchlist Lambda (enriches watchlist with price, valuation, P/E from analysis)
# Uses AWS profile: Cerebrum, region: eu-west-1

$ErrorActionPreference = "Stop"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"
$functionName = "stock-analysis-auth"

$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploy Auth/Watchlist Lambda only" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Profile: $profile | Region: $region" -ForegroundColor Gray
Write-Host ""

Push-Location $PSScriptRoot

try {
    $name = "lambda-auth"
    $tempDir = "lambda_temp_$name"
    if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
    New-Item -ItemType Directory -Path $tempDir | Out-Null

    Write-Host "Package: lambda_auth_watchlist (boto3 in runtime)" -ForegroundColor Gray
    Copy-Item "lambda_auth_watchlist.py" -Destination "$tempDir/lambda_function.py"

    $zipFile = "$name.zip"
    if (Test-Path $zipFile) { Remove-Item $zipFile }
    Push-Location $tempDir
    Compress-Archive -Path * -DestinationPath "..\$zipFile" -CompressionLevel Fastest
    Pop-Location
    Remove-Item -Recurse -Force $tempDir

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

    Write-Host ""
    Write-Host "Done. Auth Lambda (stock-analysis-auth) updated." -ForegroundColor Green
    Write-Host "GET /api/watchlist will now return price, fair value, over/undervalued, P/E." -ForegroundColor Gray
}
finally {
    Pop-Location
}
