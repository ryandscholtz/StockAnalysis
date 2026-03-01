# Configure Cognito to use SES for reliable email delivery

Write-Host "Configuring Cognito to use SES..." -ForegroundColor Green

$env:AWS_PROFILE = "Cerebrum"
$userPoolId = "eu-west-1_os9KVPAhb"
$region = "eu-west-1"
$fromEmail = "noreply@cerebrum-aec.com"

Write-Host "`nStep 1: Getting current User Pool configuration..." -ForegroundColor Cyan
$userPoolInfo = aws cognito-idp describe-user-pool --user-pool-id $userPoolId --profile Cerebrum | ConvertFrom-Json

Write-Host "Step 2: Updating User Pool to use SES..." -ForegroundColor Cyan

# Update the user pool to use SES
$updateCommand = @"
aws cognito-idp update-user-pool \
  --user-pool-id $userPoolId \
  --email-configuration EmailSendingAccount=DEVELOPER,SourceArn=arn:aws:ses:${region}:$(aws sts get-caller-identity --profile Cerebrum --query Account --output text):identity/$fromEmail,From=`"Stock Analysis <$fromEmail>`" \
  --region $region \
  --profile Cerebrum
"@

Write-Host "Executing update command..." -ForegroundColor Yellow
Invoke-Expression $updateCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSuccess! Cognito is now configured to use SES" -ForegroundColor Green
    Write-Host "From Email: $fromEmail" -ForegroundColor White
    Write-Host "`nPassword reset emails will now be sent from: Stock Analysis <$fromEmail>" -ForegroundColor Cyan
    
    Write-Host "`nTesting the configuration..." -ForegroundColor Cyan
    Write-Host "Try the forgot password flow again with one of these verified emails:" -ForegroundColor White
    Write-Host "  - ryandscholtz@gmail.com" -ForegroundColor Yellow
    Write-Host "  - admin@cerebrum-aec.com" -ForegroundColor Yellow
    
} else {
    Write-Host "`nFailed to update Cognito configuration" -ForegroundColor Red
    Write-Host "Error code: $LASTEXITCODE" -ForegroundColor Red
}