# Tail recent auto-add diagnostics from analyzer Lambda CloudWatch logs

param(
    [int]$Minutes = 30,
    [string]$Profile = "Cerebrum",
    [string]$Region = "eu-west-1",
    [string]$FunctionName = "stock-analysis-analyzer"
)

$ErrorActionPreference = "Continue"
$env:AWS_PROFILE = $Profile
$env:PYTHONIOENCODING = "utf-8"
$PSNativeCommandUseErrorActionPreference = $false

$logGroup = "/aws/lambda/$FunctionName"

Write-Host "Reading auto-add debug logs from $logGroup (last $Minutes minutes)..." -ForegroundColor Cyan
Write-Host "Filter: [AutoAdd] or [AutoAddDebug]" -ForegroundColor Gray
Write-Host ""

$startMs = [DateTimeOffset]::UtcNow.AddMinutes(-1 * $Minutes).ToUnixTimeMilliseconds()

$messages = aws logs filter-log-events `
    --log-group-name $logGroup `
    --start-time $startMs `
    --region $Region `
    --profile $Profile `
    --query "events[].message" `
    --output text 2>$null

if (-not $messages) {
    Write-Host "No log messages found in selected window." -ForegroundColor Yellow
    exit 0
}

($messages -split "`r?`n") |
    Where-Object { $_ -match "\[AutoAdd\]|\[AutoAddDebug\]" } |
    ForEach-Object { $_ }
