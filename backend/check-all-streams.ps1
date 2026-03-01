$profile = "cerebrum"
$region = "eu-west-1"
$logGroup = "/aws/lambda/stock-analysis-analyzer"

# Get ALL recent log streams
$streams = aws logs describe-log-streams `
    --log-group-name $logGroup `
    --order-by LastEventTime `
    --descending `
    --max-items 20 `
    --profile $profile `
    --region $region `
    --output json | ConvertFrom-Json

Write-Host "=== All Recent Log Streams (sorted by last event) ==="
$streams.logStreams | ForEach-Object {
    $lastEvent = if ($_.lastEventTimestamp) {
        [DateTimeOffset]::FromUnixTimeMilliseconds($_.lastEventTimestamp).ToString("yyyy-MM-dd HH:mm:ss")
    } else { "N/A" }
    $firstEvent = if ($_.firstEventTimestamp) {
        [DateTimeOffset]::FromUnixTimeMilliseconds($_.firstEventTimestamp).ToString("HH:mm:ss")
    } else { "N/A" }
    Write-Host "  $lastEvent (start $firstEvent) | $($_.logStreamName)"
}

# Get ALL events from the most recent 3 streams combined
Write-Host ""
Write-Host "=== Events from 3 most recent streams ==="
foreach ($stream in ($streams.logStreams | Select-Object -First 3)) {
    $lastEvent = [DateTimeOffset]::FromUnixTimeMilliseconds($stream.lastEventTimestamp).ToString("HH:mm:ss")
    Write-Host ""
    Write-Host "--- Stream (last event $lastEvent): $($stream.logStreamName) ---"
    $events = aws logs get-log-events `
        --log-group-name $logGroup `
        --log-stream-name $stream.logStreamName `
        --limit 200 `
        --profile $profile `
        --region $region `
        --output json | ConvertFrom-Json
    $events.events | ForEach-Object {
        $t = [DateTimeOffset]::FromUnixTimeMilliseconds($_.timestamp).ToString("HH:mm:ss.fff")
        Write-Host "[$t] $($_.message)"
    }
}
