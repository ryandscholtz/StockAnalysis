# Deploy only the API Gateway Lambda (e.g. after routing changes like /api/batch-analyze)
# Uses AWS profile: Cerebrum, region: eu-west-1

$ErrorActionPreference = "Stop"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"
$functionName = "stock-analysis-gateway"

$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploy API Gateway Lambda only" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Profile: $profile | Region: $region" -ForegroundColor Gray
Write-Host ""

Push-Location $PSScriptRoot

try {
    $name = "lambda-gateway"
    $tempDir = "lambda_temp_$name"
    if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
    New-Item -ItemType Directory -Path $tempDir | Out-Null

    # Gateway handler only uses boto3 + stdlib; boto3 is in Lambda runtime - no pip needed
    Write-Host "Package: api_gateway_lambda only (boto3 in runtime)" -ForegroundColor Gray
    Copy-Item "api_gateway_lambda.py" -Destination "$tempDir/lambda_function.py"

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
    Write-Host "Done. API Gateway Lambda (stock-analysis-gateway) updated." -ForegroundColor Green
    Write-Host "POST /api/batch-analyze will now route to the analyzer." -ForegroundColor Gray
}
finally {
    Pop-Location
}
