# Check user status in Cognito User Pool

Write-Host "Checking User Status in Cognito..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$userPoolId = "eu-west-1_os9KVPAhb"
$region = "eu-west-1"
$username = "ryandscholtz"

Write-Host "`nUser Pool: $userPoolId" -ForegroundColor Cyan
Write-Host "Region: $region" -ForegroundColor Cyan
Write-Host "Username: $username" -ForegroundColor Cyan

Write-Host "`nChecking if user exists..." -ForegroundColor Yellow

try {
    $user = aws cognito-idp admin-get-user --user-pool-id $userPoolId --username $username --region $region --profile Cerebrum 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $userInfo = $user | ConvertFrom-Json
        
        Write-Host "`nUser Found!" -ForegroundColor Green
        Write-Host "Username: $($userInfo.Username)" -ForegroundColor White
        Write-Host "User Status: $($userInfo.UserStatus)" -ForegroundColor $(if ($userInfo.UserStatus -eq "CONFIRMED") { "Green" } else { "Yellow" })
        Write-Host "Enabled: $($userInfo.Enabled)" -ForegroundColor White
        Write-Host "Created: $($userInfo.UserCreateDate)" -ForegroundColor White
        
        Write-Host "`nUser Attributes:" -ForegroundColor Cyan
        foreach ($attr in $userInfo.UserAttributes) {
            Write-Host "  $($attr.Name): $($attr.Value)" -ForegroundColor White
        }
        
        if ($userInfo.UserStatus -ne "CONFIRMED") {
            Write-Host "`nWARNING: User is not CONFIRMED!" -ForegroundColor Red
            Write-Host "User needs to verify their email or be confirmed by admin" -ForegroundColor Yellow
            
            $confirm = Read-Host "`nConfirm user now? (y/n)"
            if ($confirm -eq "y") {
                aws cognito-idp admin-confirm-sign-up --user-pool-id $userPoolId --username $username --region $region --profile Cerebrum
                Write-Host "User confirmed!" -ForegroundColor Green
            }
        }
        
    } else {
        Write-Host "`nUser NOT found!" -ForegroundColor Red
        Write-Host "Error: $user" -ForegroundColor Red
        
        Write-Host "`nLet me list all users in the pool..." -ForegroundColor Yellow
        $allUsers = aws cognito-idp list-users --user-pool-id $userPoolId --region $region --profile Cerebrum | ConvertFrom-Json
        
        Write-Host "`nTotal users: $($allUsers.Users.Count)" -ForegroundColor Cyan
        
        if ($allUsers.Users.Count -gt 0) {
            Write-Host "Users in pool:" -ForegroundColor Cyan
            foreach ($u in $allUsers.Users) {
                $email = ($u.Attributes | Where-Object { $_.Name -eq "email" }).Value
                Write-Host "  - $($u.Username) ($email) - Status: $($u.UserStatus)" -ForegroundColor White
            }
        } else {
            Write-Host "No users found in this User Pool!" -ForegroundColor Yellow
            Write-Host "`nYou need to sign up first at:" -ForegroundColor Cyan
            Write-Host "https://d3dzzi09nwx2bk.cloudfront.net/auth/signup" -ForegroundColor White
        }
    }
    
} catch {
    Write-Host "`nError checking user: $_" -ForegroundColor Red
}