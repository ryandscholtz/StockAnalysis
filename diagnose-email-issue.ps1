# Diagnose Email Delivery Issue for Cognito Password Reset

Write-Host "🔍 Diagnosing Email Delivery Issue..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$userPoolId = "eu-west-1_os9KVPAhb"

Write-Host "`n1️⃣ Checking Cognito User Pool Email Configuration..." -ForegroundColor Cyan

# Get User Pool details
$userPoolInfo = aws cognito-idp describe-user-pool --user-pool-id $userPoolId --profile Cerebrum | ConvertFrom-Json

Write-Host "`n📧 Email Configuration:" -ForegroundColor Green
$emailConfig = $userPoolInfo.UserPool.EmailConfiguration
Write-Host "Email Sending Account: $($emailConfig.EmailSendingAccount)" -ForegroundColor White
Write-Host "Source ARN: $($emailConfig.SourceArn)" -ForegroundColor White
Write-Host "Reply-To: $($emailConfig.ReplyToEmailAddress)" -ForegroundColor White
Write-Host "From Email: $($emailConfig.From)" -ForegroundColor White

Write-Host "`n2️⃣ Checking SES Status in eu-west-1..." -ForegroundColor Cyan

# Check SES sending status
try {
    $sesStatus = aws ses get-account-sending-enabled --region eu-west-1 --profile Cerebrum | ConvertFrom-Json
    Write-Host "SES Sending Enabled: $($sesStatus.Enabled)" -ForegroundColor White
} catch {
    Write-Host "⚠️  Could not check SES status - may not be configured" -ForegroundColor Yellow
}

# Check if account is in sandbox mode
try {
    $sesAccount = aws sesv2 get-account --region eu-west-1 --profile Cerebrum | ConvertFrom-Json
    Write-Host "SES Production Access: $($sesAccount.ProductionAccessEnabled)" -ForegroundColor White
    
    if (-not $sesAccount.ProductionAccessEnabled) {
        Write-Host "`n⚠️  WARNING: SES is in SANDBOX MODE" -ForegroundColor Yellow
        Write-Host "In sandbox mode, you can only send emails to:" -ForegroundColor Yellow
        Write-Host "  - Verified email addresses" -ForegroundColor Yellow
        Write-Host "  - Verified domains" -ForegroundColor Yellow
        Write-Host "`nTo fix this, you need to:" -ForegroundColor Cyan
        Write-Host "  1. Request production access for SES" -ForegroundColor White
        Write-Host "  2. OR verify the recipient email address" -ForegroundColor White
    }
} catch {
    Write-Host "⚠️  Could not check SES account status" -ForegroundColor Yellow
}

Write-Host "`n3️⃣ Checking Verified Email Identities..." -ForegroundColor Cyan

try {
    $identities = aws ses list-identities --region eu-west-1 --profile Cerebrum | ConvertFrom-Json
    
    if ($identities.Identities.Count -eq 0) {
        Write-Host "❌ No verified email identities found!" -ForegroundColor Red
        Write-Host "`nThis is likely why emails aren't being sent." -ForegroundColor Yellow
    } else {
        Write-Host "✅ Verified Identities:" -ForegroundColor Green
        foreach ($identity in $identities.Identities) {
            Write-Host "  - $identity" -ForegroundColor White
        }
    }
} catch {
    Write-Host "⚠️  Could not list SES identities" -ForegroundColor Yellow
}

Write-Host "`n4️⃣ Checking Auto-Verified Attributes..." -ForegroundColor Cyan

$autoVerified = $userPoolInfo.UserPool.AutoVerifiedAttributes
Write-Host "Auto-Verified Attributes: $($autoVerified -join ', ')" -ForegroundColor White

Write-Host "`n5️⃣ Checking MFA and Verification Settings..." -ForegroundColor Cyan

$mfaConfig = $userPoolInfo.UserPool.MfaConfiguration
Write-Host "MFA Configuration: $mfaConfig" -ForegroundColor White

Write-Host "`n📋 DIAGNOSIS SUMMARY:" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan

if ($emailConfig.EmailSendingAccount -eq "COGNITO_DEFAULT") {
    Write-Host "`n⚠️  Using Cognito Default Email (Limited)" -ForegroundColor Yellow
    Write-Host "Cognito default email has strict limits:" -ForegroundColor Yellow
    Write-Host "  - 50 emails per day" -ForegroundColor Yellow
    Write-Host "  - May be blocked or delayed" -ForegroundColor Yellow
    Write-Host "  - Not recommended for production" -ForegroundColor Yellow
    
    Write-Host "`n💡 RECOMMENDED FIX:" -ForegroundColor Green
    Write-Host "Configure SES with a verified email address:" -ForegroundColor White
    Write-Host "  1. Verify an email address in SES" -ForegroundColor White
    Write-Host "  2. Update Cognito to use SES" -ForegroundColor White
    Write-Host "  3. Request production access if needed" -ForegroundColor White
}

Write-Host "`n🔧 IMMEDIATE WORKAROUND:" -ForegroundColor Green
Write-Host "To test the functionality now:" -ForegroundColor White
Write-Host "  1. Verify your email address in SES" -ForegroundColor White
Write-Host "  2. Use that verified email for password reset" -ForegroundColor White
Write-Host "  3. Check spam/junk folders" -ForegroundColor White

Write-Host "`nWould you like me to:" -ForegroundColor Cyan
Write-Host "  A) Verify an email address in SES" -ForegroundColor White
Write-Host "  B) Configure Cognito to use SES properly" -ForegroundColor White
Write-Host "  C) Request SES production access" -ForegroundColor White