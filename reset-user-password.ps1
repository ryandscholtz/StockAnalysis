# Reset user password and set to permanent

Write-Host "Resetting User Password..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$userPoolId = "eu-west-1_os9KVPAhb"
$region = "eu-west-1"
$username = "ryandscholtz"

Write-Host "`nUser: $username" -ForegroundColor Cyan
Write-Host "Current Status: FORCE_CHANGE_PASSWORD" -ForegroundColor Yellow

Write-Host "`nSetting a new permanent password..." -ForegroundColor Cyan

# Set a new password and mark it as permanent
$newPassword = "TempPass123!"

Write-Host "Setting temporary password: $newPassword" -ForegroundColor White

aws cognito-idp admin-set-user-password `
  --user-pool-id $userPoolId `
  --username $username `
  --password $newPassword `
  --permanent `
  --region $region `
  --profile Cerebrum

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nPassword set successfully!" -ForegroundColor Green
    
    Write-Host "`nYou can now sign in with:" -ForegroundColor Cyan
    Write-Host "  Email: ryandscholtz@gmail.com" -ForegroundColor White
    Write-Host "  Password: $newPassword" -ForegroundColor White
    
    Write-Host "`nSign in at: https://d3dzzi09nwx2bk.cloudfront.net/auth/signin" -ForegroundColor Cyan
    
    Write-Host "`nAfter signing in, you can change your password to something more secure" -ForegroundColor Yellow
    
} else {
    Write-Host "`nFailed to set password" -ForegroundColor Red
}