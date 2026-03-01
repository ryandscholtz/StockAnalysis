# Check Email Configuration for Cognito

Write-Host "Checking Email Configuration..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$userPoolId = "eu-west-1_os9KVPAhb"

Write-Host "`nChecking Cognito User Pool Email Configuration..." -ForegroundColor Cyan

# Get User Pool details
$userPoolInfo = aws cognito-idp describe-user-pool --user-pool-id $userPoolId --profile Cerebrum | ConvertFrom-Json

Write-Host "`nEmail Configuration:" -ForegroundColor Green
$emailConfig = $userPoolInfo.UserPool.EmailConfiguration
Write-Host "Email Sending Account: $($emailConfig.EmailSendingAccount)" -ForegroundColor White
Write-Host "Source ARN: $($emailConfig.SourceArn)" -ForegroundColor White

Write-Host "`nChecking SES Account Status..." -ForegroundColor Cyan

try {
    $sesAccount = aws sesv2 get-account --region eu-west-1 --profile Cerebrum | ConvertFrom-Json
    Write-Host "Production Access Enabled: $($sesAccount.ProductionAccessEnabled)" -ForegroundColor White
    
    if (-not $sesAccount.ProductionAccessEnabled) {
        Write-Host "`nWARNING: SES is in SANDBOX MODE" -ForegroundColor Yellow
        Write-Host "You can only send to verified email addresses" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not check SES account status" -ForegroundColor Yellow
}

Write-Host "`nChecking Verified Email Identities..." -ForegroundColor Cyan

try {
    $identities = aws ses list-identities --region eu-west-1 --profile Cerebrum | ConvertFrom-Json
    
    if ($identities.Identities.Count -eq 0) {
        Write-Host "No verified email identities found" -ForegroundColor Red
    } else {
        Write-Host "Verified Identities:" -ForegroundColor Green
        foreach ($identity in $identities.Identities) {
            Write-Host "  - $identity" -ForegroundColor White
        }
    }
} catch {
    Write-Host "Could not list SES identities" -ForegroundColor Yellow
}

Write-Host "`nDIAGNOSIS:" -ForegroundColor Cyan

if ($emailConfig.EmailSendingAccount -eq "COGNITO_DEFAULT") {
    Write-Host "Using Cognito Default Email - This has strict limits" -ForegroundColor Yellow
    Write-Host "Recommended: Configure SES with verified email" -ForegroundColor Yellow
}