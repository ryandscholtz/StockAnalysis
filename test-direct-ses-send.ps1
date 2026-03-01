# Test sending email directly through SES to verify it works

Write-Host "Testing Direct SES Email Send..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$region = "eu-west-1"
$fromEmail = "admin@cerebrum-aec.com"
$toEmail = "ryandscholtz@gmail.com"

Write-Host "`nSending test email..." -ForegroundColor Cyan
Write-Host "From: $fromEmail" -ForegroundColor White
Write-Host "To: $toEmail" -ForegroundColor White

try {
    $result = aws ses send-email `
      --from "Stock Analysis <$fromEmail>" `
      --destination "ToAddresses=$toEmail" `
      --message "Subject={Data='Test Email from Stock Analysis',Charset=utf8},Body={Text={Data='This is a test email to verify SES is working. If you receive this, SES email delivery is functional.',Charset=utf8}}" `
      --region $region `
      --profile Cerebrum | ConvertFrom-Json
    
    Write-Host "`nSUCCESS! Email sent via SES" -ForegroundColor Green
    Write-Host "Message ID: $($result.MessageId)" -ForegroundColor Cyan
    
    Write-Host "`nCheck $toEmail inbox (and spam folder)" -ForegroundColor Yellow
    Write-Host "If you receive this test email, SES is working correctly" -ForegroundColor White
    Write-Host "The issue is with Cognito's integration with SES" -ForegroundColor White
    
} catch {
    Write-Host "`nFAILED to send email" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}