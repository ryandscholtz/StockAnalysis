# Check SES delivery status and logs

Write-Host "Checking SES Email Delivery Status..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"

Write-Host "`n1. Checking SES Sending Statistics..." -ForegroundColor Cyan

try {
    $stats = aws ses get-send-statistics --region $region --profile Cerebrum | ConvertFrom-Json
    
    if ($stats.SendDataPoints.Count -gt 0) {
        Write-Host "Recent sending activity found:" -ForegroundColor Green
        $recent = $stats.SendDataPoints | Sort-Object Timestamp -Descending | Select-Object -First 5
        
        foreach ($point in $recent) {
            Write-Host "`nTimestamp: $($point.Timestamp)" -ForegroundColor White
            Write-Host "  Delivery Attempts: $($point.DeliveryAttempts)" -ForegroundColor White
            Write-Host "  Bounces: $($point.Bounces)" -ForegroundColor Yellow
            Write-Host "  Complaints: $($point.Complaints)" -ForegroundColor Yellow
            Write-Host "  Rejects: $($point.Rejects)" -ForegroundColor Red
        }
    } else {
        Write-Host "No recent sending activity" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not get send statistics: $_" -ForegroundColor Red
}

Write-Host "`n2. Checking Email Identity Verification Status..." -ForegroundColor Cyan

$fromEmail = "noreply@cerebrum-aec.com"

try {
    $verification = aws ses get-identity-verification-attributes --identities $fromEmail --region $region --profile Cerebrum | ConvertFrom-Json
    
    $status = $verification.VerificationAttributes.$fromEmail.VerificationStatus
    Write-Host "From Email ($fromEmail) Status: $status" -ForegroundColor $(if ($status -eq "Success") { "Green" } else { "Red" })
    
    if ($status -ne "Success") {
        Write-Host "ERROR: From email is not verified!" -ForegroundColor Red
        Write-Host "This will prevent emails from being sent" -ForegroundColor Red
    }
} catch {
    Write-Host "Could not check verification status: $_" -ForegroundColor Red
}

Write-Host "`n3. Checking Recipient Email Verification..." -ForegroundColor Cyan

$recipientEmail = "ryandscholtz@gmail.com"

try {
    $recipientVerification = aws ses get-identity-verification-attributes --identities $recipientEmail --region $region --profile Cerebrum | ConvertFrom-Json
    
    $recipientStatus = $recipientVerification.VerificationAttributes.$recipientEmail.VerificationStatus
    Write-Host "Recipient Email ($recipientEmail) Status: $recipientStatus" -ForegroundColor $(if ($recipientStatus -eq "Success") { "Green" } else { "Yellow" })
} catch {
    Write-Host "Could not check recipient verification: $_" -ForegroundColor Yellow
}

Write-Host "`n4. Testing Direct SES Email Send..." -ForegroundColor Cyan

Write-Host "Attempting to send test email directly via SES..." -ForegroundColor White

$testEmailJson = @{
    Source = "Stock Analysis <$fromEmail>"
    Destination = @{
        ToAddresses = @($recipientEmail)
    }
    Message = @{
        Subject = @{
            Data = "Test Email from Stock Analysis"
            Charset = "UTF-8"
        }
        Body = @{
            Text = @{
                Data = "This is a test email to verify SES is working correctly. If you receive this, SES email delivery is functional."
                Charset = "UTF-8"
            }
        }
    }
} | ConvertTo-Json -Depth 10

$testEmailJson | Out-File -FilePath "test-email.json" -Encoding UTF8

try {
    $sendResult = aws ses send-email --cli-input-json file://test-email.json --region $region --profile Cerebrum | ConvertFrom-Json
    
    Write-Host "SUCCESS! Test email sent" -ForegroundColor Green
    Write-Host "Message ID: $($sendResult.MessageId)" -ForegroundColor White
    Write-Host "`nCheck $recipientEmail inbox (and spam folder)" -ForegroundColor Cyan
    
} catch {
    Write-Host "FAILED to send test email" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}

Remove-Item "test-email.json" -ErrorAction SilentlyContinue

Write-Host "`n5. Checking CloudWatch Logs for Cognito..." -ForegroundColor Cyan

Write-Host "Checking for recent Cognito events..." -ForegroundColor White

try {
    # Check if there are any log groups for Cognito
    $logGroups = aws logs describe-log-groups --log-group-name-prefix "/aws/cognito" --region $region --profile Cerebrum | ConvertFrom-Json
    
    if ($logGroups.logGroups.Count -gt 0) {
        Write-Host "Found Cognito log groups:" -ForegroundColor Green
        foreach ($group in $logGroups.logGroups) {
            Write-Host "  - $($group.logGroupName)" -ForegroundColor White
        }
    } else {
        Write-Host "No Cognito log groups found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not check CloudWatch logs: $_" -ForegroundColor Yellow
}

Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "If the direct SES test email was sent successfully," -ForegroundColor White
Write-Host "but Cognito emails are not arriving, the issue is with" -ForegroundColor White
Write-Host "Cognito's integration with SES, not SES itself." -ForegroundColor White