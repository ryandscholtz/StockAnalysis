# Grant Cognito permission to send emails via SES
# Cognito needs an IAM role with SES permissions

Write-Host "Setting up IAM permissions for Cognito to use SES..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"

Write-Host "`nNote: When Cognito uses SES with EmailSendingAccount=DEVELOPER," -ForegroundColor Cyan
Write-Host "it uses the AWS account's SES permissions directly." -ForegroundColor Cyan
Write-Host "No additional IAM role is needed." -ForegroundColor Cyan

Write-Host "`nThe issue might be that Cognito's email configuration" -ForegroundColor Yellow
Write-Host "was not properly applied. Let me verify and reapply..." -ForegroundColor Yellow

$userPoolId = "eu-west-1_os9KVPAhb"
$fromEmail = "admin@cerebrum-aec.com"
$accountId = aws sts get-caller-identity --profile Cerebrum --query Account --output text
$sesArn = "arn:aws:ses:${region}:${accountId}:identity/$fromEmail"

Write-Host "`nCurrent configuration:" -ForegroundColor Cyan
$userPool = aws cognito-idp describe-user-pool --user-pool-id $userPoolId --profile Cerebrum | ConvertFrom-Json
$emailConfig = $userPool.UserPool.EmailConfiguration

Write-Host "Email Sending Account: $($emailConfig.EmailSendingAccount)" -ForegroundColor White
Write-Host "Source ARN: $($emailConfig.SourceArn)" -ForegroundColor White
Write-Host "From: $($emailConfig.From)" -ForegroundColor White
Write-Host "Reply-To: $($emailConfig.ReplyToEmailAddress)" -ForegroundColor White

if ($emailConfig.EmailSendingAccount -ne "DEVELOPER") {
    Write-Host "`nConfiguration is not set to DEVELOPER mode!" -ForegroundColor Red
    Write-Host "Updating now..." -ForegroundColor Yellow
    
    aws cognito-idp update-user-pool `
      --user-pool-id $userPoolId `
      --email-configuration "EmailSendingAccount=DEVELOPER,SourceArn=$sesArn,From=Stock Analysis <$fromEmail>,ReplyToEmailAddress=$fromEmail" `
      --region $region `
      --profile Cerebrum
      
    Write-Host "Configuration updated" -ForegroundColor Green
}

Write-Host "`nAlternative: Use COGNITO_DEFAULT with custom FROM address" -ForegroundColor Cyan
Write-Host "This might work better for sandbox SES..." -ForegroundColor Yellow

$response = Read-Host "`nTry switching to COGNITO_DEFAULT mode? (y/n)"

if ($response -eq "y") {
    Write-Host "`nSwitching to COGNITO_DEFAULT..." -ForegroundColor Yellow
    
    aws cognito-idp update-user-pool `
      --user-pool-id $userPoolId `
      --email-configuration "EmailSendingAccount=COGNITO_DEFAULT,From=Stock Analysis <no-reply@verificationemail.com>" `
      --region $region `
      --profile Cerebrum
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Switched to COGNITO_DEFAULT mode" -ForegroundColor Green
        Write-Host "`nThis uses Amazon's email service (limited but reliable)" -ForegroundColor Cyan
        Write-Host "Wait 2-3 minutes, then try forgot password again" -ForegroundColor White
    }
}