# Check Lambda function logs for errors

Write-Host "Checking Lambda Function Logs..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"

Write-Host "`nFinding Lambda functions..." -ForegroundColor Cyan

$functions = aws lambda list-functions --region $region --profile Cerebrum | ConvertFrom-Json

Write-Host "Found $($functions.Functions.Count) Lambda functions:" -ForegroundColor Green

foreach ($func in $functions.Functions) {
    if ($func.FunctionName -like "*stock*" -or $func.FunctionName -like "*analysis*") {
        Write-Host "`n  - $($func.FunctionName)" -ForegroundColor White
        Write-Host "    Runtime: $($func.Runtime)" -ForegroundColor Gray
        Write-Host "    Last Modified: $($func.LastModified)" -ForegroundColor Gray
    }
}

Write-Host "`nChecking recent logs for errors..." -ForegroundColor Cyan

# Get the main API function
$apiFunction = $functions.Functions | Where-Object { $_.FunctionName -like "*StockAnalysis*" -or $_.FunctionName -like "*api*" } | Select-Object -First 1

if ($apiFunction) {
    Write-Host "`nChecking logs for: $($apiFunction.FunctionName)" -ForegroundColor Yellow
    
    $logGroup = "/aws/lambda/$($apiFunction.FunctionName)"
    
    # Get recent log streams
    $streams = aws logs describe-log-streams --log-group-name $logGroup --order-by LastEventTime --descending --max-items 5 --region $region --profile Cerebrum 2>&1 | ConvertFrom-Json
    
    if ($streams.logStreams) {
        Write-Host "Found $($streams.logStreams.Count) recent log streams" -ForegroundColor Green
        
        $latestStream = $streams.logStreams[0].logStreamName
        Write-Host "`nLatest log stream: $latestStream" -ForegroundColor Cyan
        
        # Get recent log events
        $events = aws logs get-log-events --log-group-name $logGroup --log-stream-name $latestStream --limit 50 --region $region --profile Cerebrum | ConvertFrom-Json
        
        Write-Host "`nRecent log events:" -ForegroundColor Cyan
        Write-Host "==================" -ForegroundColor Gray
        
        foreach ($event in $events.events | Select-Object -Last 20) {
            $timestamp = [DateTimeOffset]::FromUnixTimeMilliseconds($event.timestamp).LocalDateTime
            $message = $event.message
            
            if ($message -match "ERROR|Error|error|Exception|Traceback") {
                Write-Host "[$timestamp] $message" -ForegroundColor Red
            } else {
                Write-Host "[$timestamp] $message" -ForegroundColor White
            }
        }
    } else {
        Write-Host "No log streams found" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nNo API Lambda function found!" -ForegroundColor Red
    Write-Host "Available functions:" -ForegroundColor Yellow
    foreach ($func in $functions.Functions) {
        Write-Host "  - $($func.FunctionName)" -ForegroundColor White
    }
}

Write-Host "`n`nChecking API Gateway..." -ForegroundColor Cyan

$apis = aws apigateway get-rest-apis --region $region --profile Cerebrum | ConvertFrom-Json

foreach ($api in $apis.items) {
    if ($api.name -like "*stock*" -or $api.name -like "*analysis*") {
        Write-Host "`nAPI: $($api.name)" -ForegroundColor Green
        Write-Host "  ID: $($api.id)" -ForegroundColor White
        Write-Host "  Created: $($api.createdDate)" -ForegroundColor Gray
    }
}