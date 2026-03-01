# Check recent SES activity

Write-Host "Checking Recent SES Activity..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"

Write-Host "`nSES Send Statistics (last 15 minutes):" -ForegroundColor Cyan

$stats = aws ses get-send-statistics --region $region --profile Cerebrum | ConvertFrom-Json

if ($stats.SendDataPoints.Count -gt 0) {
    $recent = $stats.SendDataPoints | Sort-Object Timestamp -Descending | Select-Object -First 10
    
    Write-Host "Found $($recent.Count) recent data points:" -ForegroundColor Green
    
    foreach ($point in $recent) {
        Write-Host "`n----------------------------------------" -ForegroundColor Gray
        Write-Host "Time: $($point.Timestamp)" -ForegroundColor White
        Write-Host "Delivery Attempts: $($point.DeliveryAttempts)" -ForegroundColor Cyan
        Write-Host "Bounces: $($point.Bounces)" -ForegroundColor $(if ($point.Bounces -gt 0) { "Red" } else { "Green" })
        Write-Host "Complaints: $($point.Complaints)" -ForegroundColor $(if ($point.Complaints -gt 0) { "Red" } else { "Green" })
        Write-Host "Rejects: $($point.Rejects)" -ForegroundColor $(if ($point.Rejects -gt 0) { "Red" } else { "Green" })
    }
    
    $totalAttempts = ($recent | Measure-Object -Property DeliveryAttempts -Sum).Sum
    $totalBounces = ($recent | Measure-Object -Property Bounces -Sum).Sum
    $totalRejects = ($recent | Measure-Object -Property Rejects -Sum).Sum
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "SUMMARY:" -ForegroundColor Cyan
    Write-Host "Total Delivery Attempts: $totalAttempts" -ForegroundColor White
    Write-Host "Total Bounces: $totalBounces" -ForegroundColor $(if ($totalBounces -gt 0) { "Red" } else { "Green" })
    Write-Host "Total Rejects: $totalRejects" -ForegroundColor $(if ($totalRejects -gt 0) { "Red" } else { "Green" })
    
    if ($totalAttempts -gt 0) {
        Write-Host "`nEmails WERE sent from SES!" -ForegroundColor Green
        Write-Host "Check ryandscholtz@gmail.com inbox and spam folder" -ForegroundColor Cyan
    }
} else {
    Write-Host "No recent SES activity found" -ForegroundColor Yellow
    Write-Host "This means SES has not sent any emails recently" -ForegroundColor Yellow
}

Write-Host "`n`nCurrent Cognito Configuration:" -ForegroundColor Cyan
$userPoolId = "eu-west-1_os9KVPAhb"
$userPool = aws cognito-idp describe-user-pool --user-pool-id $userPoolId --profile Cerebrum | ConvertFrom-Json

$emailConfig = $userPool.UserPool.EmailConfiguration
Write-Host "Email Sending Account: $($emailConfig.EmailSendingAccount)" -ForegroundColor White
Write-Host "Source ARN: $($emailConfig.SourceArn)" -ForegroundColor White
Write-Host "From: $($emailConfig.From)" -ForegroundColor White

Write-Host "`n`nNEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Wait 5-10 minutes for rate limit to reset" -ForegroundColor White
Write-Host "2. Try forgot password from the web interface:" -ForegroundColor White
Write-Host "   https://d3dzzi09nwx2bk.cloudfront.net/auth/forgot-password" -ForegroundColor Cyan
Write-Host "3. Use email: ryandscholtz@gmail.com" -ForegroundColor White
Write-Host "4. Check inbox AND spam folder" -ForegroundColor White
Write-Host "5. Look for sender: Stock Analysis <admin@cerebrum-aec.com>" -ForegroundColor White