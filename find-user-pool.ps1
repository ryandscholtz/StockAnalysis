# Find the User Pool across all regions

Write-Host "Searching for User Pool: us-east-1_HwPb4qQo1" -ForegroundColor Yellow

$env:AWS_PROFILE = "Cerebrum"
$targetPoolId = "us-east-1_HwPb4qQo1"

$regions = @(
    "us-east-1",
    "us-east-2", 
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-west-2",
    "eu-central-1"
)

Write-Host "`nSearching across regions..." -ForegroundColor Cyan

foreach ($region in $regions) {
    Write-Host "Checking $region..." -ForegroundColor Gray
    
    try {
        $pools = aws cognito-idp list-user-pools --max-results 60 --region $region --profile Cerebrum 2>$null | ConvertFrom-Json
        
        foreach ($pool in $pools.UserPools) {
            if ($pool.Id -eq $targetPoolId) {
                Write-Host "`nFOUND IT!" -ForegroundColor Green
                Write-Host "Region: $region" -ForegroundColor Cyan
                Write-Host "Pool ID: $($pool.Id)" -ForegroundColor White
                Write-Host "Pool Name: $($pool.Name)" -ForegroundColor White
                
                # Get clients
                $clients = aws cognito-idp list-user-pool-clients --user-pool-id $targetPoolId --region $region --profile Cerebrum | ConvertFrom-Json
                
                if ($clients.UserPoolClients.Count -gt 0) {
                    Write-Host "`nClients:" -ForegroundColor Cyan
                    foreach ($client in $clients.UserPoolClients) {
                        Write-Host "  - $($client.ClientName): $($client.ClientId)" -ForegroundColor White
                    }
                }
                
                exit 0
            }
        }
    } catch {
        # Region might not be enabled, skip
    }
}

Write-Host "`nUser Pool not found in any region!" -ForegroundColor Red
Write-Host "`nLet me list all User Pools in eu-west-1..." -ForegroundColor Yellow

$pools = aws cognito-idp list-user-pools --max-results 60 --region eu-west-1 --profile Cerebrum | ConvertFrom-Json

Write-Host "`nUser Pools in eu-west-1:" -ForegroundColor Cyan
foreach ($pool in $pools.UserPools) {
    Write-Host "  - $($pool.Name): $($pool.Id)" -ForegroundColor White
}