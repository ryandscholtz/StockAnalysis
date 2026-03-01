# Check the main API Lambda function logs

Write-Host "Checking API Lambda Logs..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"
$functionName = "stock-analysis-api-production"
$logGroup = "/aws/lambda/$functionName"

Write-Host "`nFunction: $functionName" -ForegroundColor Cyan
Write-Host "Log Group: $logGroup" -ForegroundColor Cyan

# Get recent log streams
Write-Host "`nGetting recent log streams..." -ForegroundColor Yellow

$streams = aws logs describe-log-streams --log-group-name $logGroup --order-by LastEventTime --descending --max-items 10 --region $region --profile Cerebrum | ConvertFrom-Json

if ($streams.logStreams) {
    Write-Host "Found $($streams.logStreams.Count) recent log streams" -ForegroundColor Green
    
    foreach ($stream in $streams.logStreams | Select-Object -First 3) {
        $streamName = $stream.logStreamName
        $lastEvent = [DateTimeOffset]::FromUnixTimeMilliseconds($stream.lastEventTimestamp).LocalDateTime
        
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "Stream: $streamName" -ForegroundColor White
        Write-Host "Last Event: $lastEvent" -ForegroundColor Gray
        Write-Host "========================================" -ForegroundColor Cyan
        
        # Get log events
        $events = aws logs get-log-events --log-group-name $logGroup --log-stream-name $streamName --limit 100 --region $region --profile Cerebrum | ConvertFrom-Json
        
        foreach ($event in $events.events | Select-Object -Last 30) {
            $timestamp = [DateTimeOffset]::FromUnixTimeMilliseconds($event.timestamp).LocalDateTime.ToString("HH:mm:ss")
            $message = $event.message.Trim()
            
            if ($message -match "ERROR|Error|error|Exception|Traceback|Failed|failed") {
                Write-Host "[$timestamp] $message" -ForegroundColor Red
            } elseif ($message -match "WARNING|Warning|warn") {
                Write-Host "[$timestamp] $message" -ForegroundColor Yellow
            } else {
                Write-Host "[$timestamp] $message" -ForegroundColor White
            }
        }
    }
} else {
    Write-Host "No log streams found!" -ForegroundColor Red
}

Write-Host "`n`nTesting Lambda function directly..." -ForegroundColor Cyan

$testPayload = @{
    httpMethod = "GET"
    path = "/health"
    headers = @{}
    queryStringParameters = @{}
} | ConvertTo-Json

$testPayload | Out-File -FilePath "test-lambda-payload.json" -Encoding UTF8

Write-Host "Invoking Lambda function..." -ForegroundColor Yellow

aws lambda invoke --function-name $functionName --payload file://test-lambda-payload.json --region $region --profile Cerebrum response.json

if (Test-Path "response.json") {
    Write-Host "`nLambda Response:" -ForegroundColor Green
    Get-Content "response.json" | Write-Host -ForegroundColor White
    
    Remove-Item "response.json" -ErrorAction SilentlyContinue
}

Remove-Item "test-lambda-payload.json" -ErrorAction SilentlyContinue