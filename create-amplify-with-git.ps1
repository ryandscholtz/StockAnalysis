# Create New Amplify App with Git Integration
$region = "eu-west-1"
$profile = "Cerebrum"
$repoUrl = "https://github.com/YourUsername/StockAnalysis"  # Update with your actual repo URL

Write-Host "Creating new Amplify app with Git integration..." -ForegroundColor Cyan

# This requires your GitHub repository URL
Write-Host "To create an app with Git integration, run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "aws amplify create-app --name 'stock-analysis-auto-deploy' --region $region --profile $profile" -ForegroundColor White
Write-Host ""
Write-Host "Then connect the repository:" -ForegroundColor Yellow
Write-Host "aws amplify create-branch --app-id <NEW_APP_ID> --branch-name main --repository $repoUrl --region $region --profile $profile" -ForegroundColor White
Write-Host ""
Write-Host "This will enable automatic deployments on every push to main branch." -ForegroundColor Green