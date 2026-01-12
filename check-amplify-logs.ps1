# Check AWS Amplify Deployment Logs
# ARN: arn:aws:amplify:eu-west-1:295202642810:apps/d1h3822e5hvb4m

Write-Host "AWS Amplify Deployment Log Checker" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

$appId = "d1h3822e5hvb4m"
$region = "eu-west-1"
$accountId = "295202642810"
$arn = "arn:aws:amplify:eu-west-1:295202642810:apps/d1h3822e5hvb4m"

Write-Host ""
Write-Host "App Information:" -ForegroundColor Yellow
Write-Host "- ARN: $arn" -ForegroundColor Cyan
Write-Host "- App ID: $appId" -ForegroundColor Cyan
Write-Host "- Region: $region" -ForegroundColor Cyan
Write-Host "- Account: $accountId" -ForegroundColor Cyan
Write-Host "- Branch: main" -ForegroundColor Cyan

Write-Host ""
Write-Host "Direct Links:" -ForegroundColor Yellow
Write-Host "- App Console: https://$region.console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
Write-Host "- Deployments: https://$region.console.aws.amazon.com/amplify/home?region=$region#/$appId/YnJhbmNoZXM/main" -ForegroundColor Cyan
Write-Host "- App URL: https://main.$appId.amplifyapp.com" -ForegroundColor Cyan

Write-Host ""
Write-Host "To check deployment logs:" -ForegroundColor Yellow
Write-Host "1. Open the App Console link above" -ForegroundColor White
Write-Host "2. Click on the 'main' branch" -ForegroundColor White
Write-Host "3. Look for the latest deployment job" -ForegroundColor White
Write-Host "4. Click on the job to see detailed logs" -ForegroundColor White

Write-Host ""
Write-Host "Common log sections to check:" -ForegroundColor Yellow
Write-Host "- Provision: Environment setup" -ForegroundColor White
Write-Host "- Build: npm ci and npm run build output" -ForegroundColor White
Write-Host "- Deploy: File deployment to CDN" -ForegroundColor White
Write-Host "- Verify: Final verification checks" -ForegroundColor White

Write-Host ""
Write-Host "If you have AWS CLI configured, run:" -ForegroundColor Yellow
Write-Host "aws amplify list-jobs --app-id $appId --branch-name main --region $region" -ForegroundColor Cyan

Write-Host ""
Write-Host "Current amplify.yml configuration:" -ForegroundColor Yellow
if (Test-Path "amplify.yml") {
    Get-Content "amplify.yml"
} else {
    Write-Host "amplify.yml not found!" -ForegroundColor Red
}