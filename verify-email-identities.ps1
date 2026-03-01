# Check each email identity individually

Write-Host "Checking Email Verification Status..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"

$emails = @(
    "ryandscholtz@gmail.com",
    "admin@cerebrum-aec.com",
    "noreply@cerebrum-aec.com"
)

Write-Host "`nChecking each email individually:" -ForegroundColor Cyan

$verifiedEmails = @()

foreach ($email in $emails) {
    try {
        $result = aws ses get-identity-verification-attributes --identities $email --region $region --profile Cerebrum | ConvertFrom-Json
        $status = $result.VerificationAttributes.$email.VerificationStatus
        
        if ($status -eq "Success") {
            Write-Host "$email : SUCCESS" -ForegroundColor Green
            $verifiedEmails += $email
        } else {
            Write-Host "$email : $status" -ForegroundColor Red
        }
    } catch {
        Write-Host "$email : ERROR - $_" -ForegroundColor Red
    }
}

if ($verifiedEmails.Count -gt 0) {
    Write-Host "`nVerified emails found: $($verifiedEmails.Count)" -ForegroundColor Green
    
    # Use the first verified email
    $workingEmail = $verifiedEmails[0]
    Write-Host "Using: $workingEmail" -ForegroundColor Cyan
    
    Write-Host "`nReconfiguring Cognito..." -ForegroundColor Yellow
    
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
        Write-Host "`nSUCCESS! Cognito configured with verified email" -ForegroundColor Green
        Write-Host "From: Stock Analysis <$workingEmail>" -ForegroundColor Cyan
        
        Write-Host "`nTesting email send..." -ForegroundColor Yellow
        node test-password-reset-email.js
    }
} else {
    Write-Host "`nNo verified emails found!" -ForegroundColor Red
    Write-Host "`nLet me verify ryandscholtz@gmail.com now..." -ForegroundColor Yellow
    
    aws ses verify-email-identity --email-address "ryandscholtz@gmail.com" --region $region --profile Cerebrum
    
    Write-Host "`nVerification email sent to ryandscholtz@gmail.com" -ForegroundColor Green
    Write-Host "Check your inbox and click the verification link" -ForegroundColor Cyan
    Write-Host "Then run this script again" -ForegroundColor White
}