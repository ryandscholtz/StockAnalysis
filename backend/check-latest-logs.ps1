$profile = "cerebrum"
$region = "eu-west-1"
$logGroup = "/aws/lambda/stock-analysis-analyzer"

# Get most recent log stream
$streams = aws logs describe-log-streams `
    --log-group-name $logGroup `
    --order-by LastEventTime `
    --descending `
    --max-items 5 `
    --profile $profile `
    --region $region `
    --output json | ConvertFrom-Json

Write-Host "=== Recent Streams ==="
$streams.logStreams | ForEach-Object {
    $t = [DateTimeOffset]::FromUnixTimeMilliseconds($_.lastEventTimestamp).ToString("HH:mm:ss")
    Write-Host "  $($_.logStreamName) - $t"
}

# Get events from 2 most recent streams to catch the analysis
foreach ($stream in ($streams.logStreams | Select-Object -First 2)) {
    Write-Host ""
    Write-Host "=== Stream: $($stream.logStreamName) ==="
    $events = aws logs get-log-events `
        --log-group-name $logGroup `
        --log-stream-name $stream.logStreamName `
        --limit 150 `
        --profile $profile `
        --region $region `
        --output json | ConvertFrom-Json
    $events.events | ForEach-Object {
        $t = [DateTimeOffset]::FromUnixTimeMilliseconds($_.timestamp).ToString("HH:mm:ss.fff")
        Write-Host "[$t] $($_.message)"
    }
}
