# Switch back to Cognito Default Email
# This is more reliable for testing, even though it has limits

Write-Host "Switching to Cognito Default Email Service..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"
$userPoolId = "eu-west-1_os9KVPAhb"

Write-Host "`nCognito Default Email:" -ForegroundColor Cyan
Write-Host "- Uses Amazon's email infrastructure" -ForegroundColor White
Write-Host "- Limited to 50 emails per day" -ForegroundColor White
Write-Host "- More reliable for testing" -ForegroundColor White
Write-Host "- No SES configuration needed" -ForegroundColor White

Write-Host "`nUpdating Cognito User Pool..." -ForegroundColor Yellow

aws cognito-idp update-user-pool `
  --user-pool-id $userPoolId `
  --email-configuration "EmailSendingAccount=COGNITO_DEFAULT" `
  --region $region `
  --profile Cerebrum

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSUCCESS! Switched to COGNITO_DEFAULT" -ForegroundColor Green
    
    Write-Host "`nVerifying configuration..." -ForegroundColor Cyan
    $userPool = aws cognito-idp describe-user-pool --user-pool-id $userPoolId --profile Cerebrum | ConvertFrom-Json
    $emailConfig = $userPool.UserPool.EmailConfiguration
    
    Write-Host "Email Sending Account: $($emailConfig.EmailSendingAccount)" -ForegroundColor White
    
    Write-Host "`nWait 2-3 minutes for configuration to propagate..." -ForegroundColor Yellow
    Write-Host "Then try the forgot password flow at:" -ForegroundColor White
    Write-Host "https://d3dzzi09nwx2bk.cloudfront.net/auth/forgot-password" -ForegroundColor Cyan
    
    Write-Host "`nUse email: ryandscholtz@gmail.com" -ForegroundColor White
    Write-Host "Check inbox AND spam folder" -ForegroundColor Yellow
    Write-Host "Look for sender: no-reply@verificationemail.com" -ForegroundColor White
    
} else {
    Write-Host "`nFailed to update configuration" -ForegroundColor Red
}