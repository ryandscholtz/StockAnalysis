# Configure Cognito to use SES for email delivery

Write-Host "Configuring Cognito to use SES..." -ForegroundColor Green

$env:AWS_PROFILE = "Cerebrum"
$userPoolId = "eu-west-1_os9KVPAhb"
$region = "eu-west-1"
$fromEmail = "noreply@cerebrum-aec.com"

# Get AWS account ID
$accountId = aws sts get-caller-identity --profile Cerebrum --query Account --output text

Write-Host "Account ID: $accountId" -ForegroundColor White
Write-Host "From Email: $fromEmail" -ForegroundColor White

# Build the SES ARN
$sesArn = "arn:aws:ses:${region}:${accountId}:identity/$fromEmail"
Write-Host "SES ARN: $sesArn" -ForegroundColor White

Write-Host "`nUpdating Cognito User Pool..." -ForegroundColor Cyan

# Update user pool with proper email configuration
aws cognito-idp update-user-pool `
  --user-pool-id $userPoolId `
  --email-configuration "EmailSendingAccount=DEVELOPER,SourceArn=$sesArn,From=Stock Analysis <$fromEmail>" `
  --region $region `
  --profile Cerebrum

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSuccess! Cognito configured to use SES" -ForegroundColor Green
    Write-Host "`nPassword reset emails will be sent from:" -ForegroundColor Cyan
    Write-Host "Stock Analysis <$fromEmail>" -ForegroundColor White
    
    Write-Host "`nNOTE: SES is in sandbox mode" -ForegroundColor Yellow
    Write-Host "You can only send to these verified addresses:" -ForegroundColor Yellow
    Write-Host "  - ryandscholtz@gmail.com" -ForegroundColor White
    Write-Host "  - admin@cerebrum-aec.com" -ForegroundColor White
    
    Write-Host "`nTry the forgot password flow again!" -ForegroundColor Green
} else {
    Write-Host "`nFailed to update configuration" -ForegroundColor Red
}