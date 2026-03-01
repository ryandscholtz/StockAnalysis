$profile = "cerebrum"
$region = "eu-west-1"
$logGroup = "/aws/lambda/stock-analysis-analyzer"

# Check the Feb 27 stream that ran for 5+ minutes
$streamName = "2026/02/27/[`$LATEST]0dd2fecf1dbc4e0e8d937e45171bd616"

Write-Host "=== Feb 27 long-running stream ==="
$events = aws logs get-log-events `
    --log-group-name $logGroup `
    --log-stream-name $streamName `
    --limit 200 `
    --profile $profile `
    --region $region `
    --output json | ConvertFrom-Json

$events.events | ForEach-Object {
    $t = [DateTimeOffset]::FromUnixTimeMilliseconds($_.timestamp).ToString("HH:mm:ss.fff")
    Write-Host "[$t] $($_.message)"
}
