param([string]$FunctionName = "stock-analysis-stock-data", [int]$Minutes = 5)

$startMs = [long]([DateTimeOffset]::UtcNow.AddMinutes(-$Minutes).ToUnixTimeMilliseconds())

aws logs filter-log-events `
    --log-group-name "/aws/lambda/$FunctionName" `
    --start-time $startMs `
    --profile Cerebrum --region eu-west-1 `
    --query "events[*].message" `
    --output text 2>&1 | Select-Object -Last 50
