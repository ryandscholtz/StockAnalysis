$profile = "cerebrum"
$region = "eu-west-1"
$logGroup = "/aws/lambda/stock-analysis-analyzer"

$streams = aws logs describe-log-streams `
    --log-group-name $logGroup `
    --order-by LastEventTime `
    --descending `
    --max-items 3 `
    --profile $profile `
    --region $region `
    --output json | ConvertFrom-Json

$latestStream = $streams.logStreams[0].logStreamName
Write-Host "Log stream: $latestStream"

$events = aws logs get-log-events `
    --log-group-name $logGroup `
    --log-stream-name $latestStream `
    --limit 100 `
    --profile $profile `
    --region $region `
    --output json | ConvertFrom-Json

$events.events | ForEach-Object { $_.message }
