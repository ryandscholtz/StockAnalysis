# Check all verified email identities and their status

Write-Host "Checking All Email Identity Verification Status..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"

# Get all identities
$identities = aws ses list-identities --region $region --profile Cerebrum | ConvertFrom-Json

Write-Host "`nAll Identities:" -ForegroundColor Cyan
foreach ($identity in $identities.Identities) {
    Write-Host "  - $identity" -ForegroundColor White
}

# Get verification status for all
Write-Host "`nVerification Status:" -ForegroundColor Cyan

$identityList = $identities.Identities -join " "
$verification = aws ses get-identity-verification-attributes --identities $identityList --region $region --profile Cerebrum | ConvertFrom-Json

foreach ($identity in $identities.Identities) {
    $status = $verification.VerificationAttributes.$identity.VerificationStatus
    $color = if ($status -eq "Success") { "Green" } else { "Red" }
    Write-Host "$identity : $status" -ForegroundColor $color
}

Write-Host "`nLooking for a working verified email..." -ForegroundColor Cyan

$workingEmail = $null
foreach ($identity in $identities.Identities) {
    $status = $verification.VerificationAttributes.$identity.VerificationStatus
    if ($status -eq "Success" -and $identity -like "*@*") {
        $workingEmail = $identity
        Write-Host "Found working email: $workingEmail" -ForegroundColor Green
        break
    }
}

if ($workingEmail) {
    Write-Host "`nReconfiguring Cognito to use: $workingEmail" -ForegroundColor Yellow
    
    $userPoolId = "eu-west-1_os9KVPAhb"
    $accountId = aws sts get-caller-identity --profile Cerebrum --query Account --output text
    $sesArn = "arn:aws:ses:${region}:${accountId}:identity/$workingEmail"
    
    Write-Host "SES ARN: $sesArn" -ForegroundColor White
    
    aws cognito-idp update-user-pool `
      --user-pool-id $userPoolId `
      --email-configuration "EmailSendingAccount=DEVELOPER,SourceArn=$sesArn,From=Stock Analysis <$workingEmail>" `
      --region $region `
      --profile Cerebrum
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nSUCCESS! Cognito reconfigured" -ForegroundColor Green
        Write-Host "Emails will now be sent from: $workingEmail" -ForegroundColor Cyan
        Write-Host "`nTry the forgot password flow again!" -ForegroundColor Green
    }
} else {
    Write-Host "`nNo working verified email found!" -ForegroundColor Red
    Write-Host "You need to verify an email address first" -ForegroundColor Yellow
}