# Setup Amplify Git Integration for Auto-Deployment
$appId = "d2w7qchby0cr5y"
$region = "eu-west-1"
$profile = "Cerebrum"

Write-Host "Setting up Amplify Git Integration..." -ForegroundColor Cyan

# First, we need to delete the current app and recreate it with Git integration
# Or update the existing app to use Git

Write-Host "Current setup uses manual zip deployments." -ForegroundColor Yellow
Write-Host "For auto-deployment, we need to connect to your GitHub repository." -ForegroundColor Yellow
Write-Host ""

# Check if we can update the existing app to use Git
Write-Host "Option 1: Connect existing app to Git repository" -ForegroundColor Green
Write-Host "This requires:" -ForegroundColor White
Write-Host "  1. GitHub repository URL" -ForegroundColor White
Write-Host "  2. GitHub access token or OAuth setup" -ForegroundColor White
Write-Host "  3. Branch specification (main)" -ForegroundColor White
Write-Host ""

Write-Host "Option 2: Create new Amplify app with Git integration" -ForegroundColor Green
Write-Host "This would:" -ForegroundColor White
Write-Host "  1. Create fresh app connected to your GitHub repo" -ForegroundColor White
Write-Host "  2. Enable automatic deployments on push to main" -ForegroundColor White
Write-Host "  3. Provide build logs and deployment history" -ForegroundColor White
Write-Host ""

Write-Host "Current App Details:" -ForegroundColor Cyan
aws amplify get-app --app-id $appId --region $region --profile $profile --query "app.{Name:name,Domain:defaultDomain,AutoBuild:enableBranchAutoBuild}"

Write-Host ""
Write-Host "To enable auto-deployment, you need to:" -ForegroundColor Yellow
Write-Host "1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor White
Write-Host "2. Click 'Connect repository' or 'App settings' > 'General'" -ForegroundColor White
Write-Host "3. Connect your GitHub repository" -ForegroundColor White
Write-Host "4. Select the main branch" -ForegroundColor White
Write-Host "5. Configure build settings (amplify.yml)" -ForegroundColor White
Write-Host ""

Write-Host "Alternative: Use GitHub Actions for deployment" -ForegroundColor Green
Write-Host "This would deploy to Amplify automatically on every push to main" -ForegroundColor White