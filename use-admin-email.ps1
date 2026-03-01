# Configure Cognito to use admin@cerebrum-aec.com as sender

Write-Host "Configuring Cognito to use admin@cerebrum-aec.com..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"
$userPoolId = "eu-west-1_os9KVPAhb"
$fromEmail = "admin@cerebrum-aec.com"

$accountId = aws sts get-caller-identity --profile Cerebrum --query Account --output text
$sesArn = "arn:aws:ses:${region}:${accountId}:identity/$fromEmail"

Write-Host "From Email: $fromEmail" -ForegroundColor White
Write-Host "SES ARN: $sesArn" -ForegroundColor White

aws cognito-idp update-user-pool `
  --user-pool-id $userPoolId `
  --email-configuration "EmailSendingAccount=DEVELOPER,SourceArn=$sesArn,From=Stock Analysis <$fromEmail>" `
  --region $region `
  --profile Cerebrum

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSUCCESS! Cognito configured" -ForegroundColor Green
    Write-Host "Emails will be sent from: Stock Analysis <$fromEmail>" -ForegroundColor Cyan
    
    Write-Host "`nNow testing password reset to ryandscholtz@gmail.com..." -ForegroundColor Yellow
    
    # Test the forgot password flow
    node test-password-reset-email.js
    
    Write-Host "`nCheck ryandscholtz@gmail.com inbox now!" -ForegroundColor Green
    Write-Host "Look for email from: Stock Analysis <admin@cerebrum-aec.com>" -ForegroundColor Cyan
    Write-Host "Subject: Your verification code" -ForegroundColor White
}