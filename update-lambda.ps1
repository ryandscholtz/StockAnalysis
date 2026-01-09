# PowerShell script to update Lambda function with retry logic
param(
    [int]$MaxRetries = 3,
    [int]$DelaySeconds = 5
)

$FunctionName = "stock-analysis-api-production"
$ZipFile = "backend/dist.zip"

Write-Host "Updating Lambda function: $FunctionName"
Write-Host "Using zip file: $ZipFile"

for ($i = 1; $i -le $MaxRetries; $i++) {
    Write-Host "Attempt $i of $MaxRetries..."
    
    try {
        $result = aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Lambda function updated successfully!" -ForegroundColor Green
            Write-Host $result
            exit 0
        } else {
            Write-Host "❌ Update failed with exit code: $LASTEXITCODE" -ForegroundColor Red
            Write-Host $result
        }
    } catch {
        Write-Host "❌ Exception occurred: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    if ($i -lt $MaxRetries) {
        Write-Host "Waiting $DelaySeconds seconds before retry..." -ForegroundColor Yellow
        Start-Sleep -Seconds $DelaySeconds
    }
}

Write-Host "❌ All retry attempts failed. Lambda function was not updated." -ForegroundColor Red
exit 1