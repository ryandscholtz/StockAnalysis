$ErrorActionPreference = "Stop"
$profile = "cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"
$funcName = "stock-analysis-analyzer"
$tempDir = "lambda_temp_analysis_deploy"

Set-Location "C:\Users\Admin\Documents\GitHub\StockAnalysis\backend"

if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
New-Item -ItemType Directory -Path $tempDir | Out-Null
Copy-Item "lambda_analysis.py" -Destination "$tempDir\lambda_function.py"

$zipFile = "lambda-analysis-update.zip"
if (Test-Path $zipFile) { Remove-Item $zipFile }

Push-Location $tempDir
Compress-Archive -Path * -DestinationPath "..\$zipFile" -CompressionLevel Fastest
Pop-Location
Remove-Item -Recurse -Force $tempDir

$size = (Get-Item $zipFile).Length
Write-Host "Package: $size bytes"

$s3Key = "microservices/$zipFile"
aws s3 cp $zipFile "s3://$s3Bucket/$s3Key" --profile $profile --region $region --quiet
Write-Host "Uploaded to S3"

aws lambda update-function-code `
    --function-name $funcName `
    --s3-bucket $s3Bucket `
    --s3-key $s3Key `
    --profile $profile `
    --region $region `
    --query "LastModified" `
    --output text

Write-Host "Done! Lambda $funcName updated."
