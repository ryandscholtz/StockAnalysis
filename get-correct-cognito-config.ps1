# Get the correct Cognito configuration from us-east-1

Write-Host "Getting Cognito Configuration from us-east-1..." -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$userPoolId = "us-east-1_HwPb4qQo1"
$region = "us-east-1"

Write-Host "`nFetching User Pool details..." -ForegroundColor Cyan

$userPool = aws cognito-idp describe-user-pool --user-pool-id $userPoolId --region $region --profile Cerebrum | ConvertFrom-Json

Write-Host "`nUser Pool Information:" -ForegroundColor Green
Write-Host "User Pool ID: $userPoolId" -ForegroundColor White
Write-Host "Region: $region" -ForegroundColor White
Write-Host "Name: $($userPool.UserPool.Name)" -ForegroundColor White

Write-Host "`nGetting User Pool Clients..." -ForegroundColor Cyan

$clients = aws cognito-idp list-user-pool-clients --user-pool-id $userPoolId --region $region --profile Cerebrum | ConvertFrom-Json

if ($clients.UserPoolClients.Count -gt 0) {
    Write-Host "Found $($clients.UserPoolClients.Count) client(s):" -ForegroundColor Green
    
    foreach ($client in $clients.UserPoolClients) {
        Write-Host "`nClient Name: $($client.ClientName)" -ForegroundColor White
        Write-Host "Client ID: $($client.ClientId)" -ForegroundColor Cyan
    }
    
    $clientId = $clients.UserPoolClients[0].ClientId
} else {
    Write-Host "No clients found!" -ForegroundColor Red
    exit 1
}

Write-Host "`nGetting Identity Pool..." -ForegroundColor Cyan

$identityPools = aws cognito-identity list-identity-pools --max-results 10 --region $region --profile Cerebrum | ConvertFrom-Json

$identityPoolId = $null
foreach ($pool in $identityPools.IdentityPools) {
    if ($pool.IdentityPoolName -like "*stock*" -or $pool.IdentityPoolName -like "*analysis*") {
        $identityPoolId = $pool.IdentityPoolId
        Write-Host "Found Identity Pool: $($pool.IdentityPoolName)" -ForegroundColor Green
        Write-Host "Identity Pool ID: $identityPoolId" -ForegroundColor Cyan
        break
    }
}

if (-not $identityPoolId) {
    Write-Host "No matching identity pool found, using first available..." -ForegroundColor Yellow
    if ($identityPools.IdentityPools.Count -gt 0) {
        $identityPoolId = $identityPools.IdentityPools[0].IdentityPoolId
        Write-Host "Identity Pool ID: $identityPoolId" -ForegroundColor Cyan
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CORRECT CONFIGURATION:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEXT_PUBLIC_USER_POOL_ID=$userPoolId" -ForegroundColor Green
Write-Host "NEXT_PUBLIC_USER_POOL_CLIENT_ID=$clientId" -ForegroundColor Green
Write-Host "NEXT_PUBLIC_IDENTITY_POOL_ID=$identityPoolId" -ForegroundColor Green
Write-Host "NEXT_PUBLIC_AWS_REGION=$region" -ForegroundColor Green

Write-Host "`nUpdating frontend/.env.production..." -ForegroundColor Yellow

$envContent = @"
NEXT_PUBLIC_API_URL=https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production
NEXT_PUBLIC_USER_POOL_ID=$userPoolId
NEXT_PUBLIC_USER_POOL_CLIENT_ID=$clientId
NEXT_PUBLIC_IDENTITY_POOL_ID=$identityPoolId
NEXT_PUBLIC_AWS_REGION=$region
"@

$envContent | Out-File -FilePath "frontend/.env.production" -Encoding UTF8

Write-Host "Updated frontend/.env.production" -ForegroundColor Green

Write-Host "`nNow rebuilding and redeploying frontend..." -ForegroundColor Yellow