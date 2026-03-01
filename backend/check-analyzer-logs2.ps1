$profile = "cerebrum"
$region = "eu-west-1"
$logGroup = "/aws/lambda/stock-analysis-analyzer"

# Get multiple streams
$streams = aws logs describe-log-streams `
    --log-group-name $logGroup `
    --order-by LastEventTime `
    --descending `
    --max-items 10 `
    --profile $profile `
    --region $region `
    --output json | ConvertFrom-Json

# Show all streams with their last event time
Write-Host "=== Log Streams ==="
$streams.logStreams | ForEach-Object {
    $lastEvent = if ($_.lastEventTimestamp) {
        [DateTimeOffset]::FromUnixTimeMilliseconds($_.lastEventTimestamp).ToString("HH:mm:ss")
    } else { "N/A" }
    Write-Host "  $($_.logStreamName) - last: $lastEvent"
}

# Get events from the most recent stream
Write-Host ""
Write-Host "=== Latest Stream Events ==="
$latestStream = $streams.logStreams[0].logStreamName

$events = aws logs get-log-events `
    --log-group-name $logGroup `
    --log-stream-name $latestStream `
    --limit 200 `
    --profile $profile `
    --region $region `
    --output json | ConvertFrom-Json

$events.events | ForEach-Object {
    $time = [DateTimeOffset]::FromUnixTimeMilliseconds($_.timestamp).ToString("HH:mm:ss.fff")
    Write-Host "[$time] $($_.message)"
}
