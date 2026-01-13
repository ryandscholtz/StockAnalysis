# Check CloudFront deployment status

param(
    [string]$Profile = "Cerebrum"
)

Write-Host "☁️  Checking CloudFront deployment status..." -ForegroundColor Green

# Read deployment info if available
if (Test-Path "deployment-info.json") {
    $deploymentInfo = Get-Content "deployment-info.json" | ConvertFrom-Json
    $distributionId = $deploymentInfo.DistributionId
    $domainName = $deploymentInfo.CloudFrontDomain
    
    Write-Host "📋 Found deployment info:" -ForegroundColor Yellow
    Write-Host "   Distribution ID: $distributionId" -ForegroundColor Cyan
    Write-Host "   Domain: $domainName" -ForegroundColor Cyan
    Write-Host ""
    
    # Get current status
    Write-Host "🔍 Checking current status..." -ForegroundColor Yellow
    
    try {
        $distribution = aws cloudfront get-distribution --id $distributionId --profile $Profile | ConvertFrom-Json
        $status = $distribution.Distribution.Status
        $lastModified = $distribution.Distribution.LastModifiedTime
        
        Write-Host "📊 Current Status: $status" -ForegroundColor $(if ($status -eq "Deployed") { "Green" } else { "Yellow" })
        Write-Host "🕒 Last Modified: $lastModified" -ForegroundColor Cyan
        
        if ($status -eq "Deployed") {
            Write-Host ""
            Write-Host "🎉 Deployment is complete!" -ForegroundColor Green
            Write-Host "🌐 Your app is available at: https://$domainName" -ForegroundColor Green
            
            # Test the URL
            Write-Host ""
            Write-Host "🧪 Testing CloudFront URL..." -ForegroundColor Yellow
            try {
                $response = Invoke-WebRequest -Uri "https://$domainName" -Method Head -TimeoutSec 10
                Write-Host "✅ CloudFront URL is responding (Status: $($response.StatusCode))" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  CloudFront URL not yet responding: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "   This is normal for new deployments. Try again in a few minutes." -ForegroundColor White
            }
        } else {
            Write-Host ""
            Write-Host "⏳ Deployment still in progress..." -ForegroundColor Yellow
            Write-Host "   Typical deployment time: 10-15 minutes" -ForegroundColor White
            Write-Host "   Run this script again in a few minutes to check status" -ForegroundColor White
        }
        
    } catch {
        Write-Host "❌ Error checking distribution status: $($_.Exception.Message)" -ForegroundColor Red
    }
    
} else {
    Write-Host "❌ No deployment-info.json found." -ForegroundColor Red
    Write-Host "   Please run the deployment script first." -ForegroundColor Yellow
    
    # List all distributions as fallback
    Write-Host ""
    Write-Host "📋 Available CloudFront distributions:" -ForegroundColor Yellow
    try {
        $distributions = aws cloudfront list-distributions --profile $Profile | ConvertFrom-Json
        
        if ($distributions.DistributionList.Items.Count -gt 0) {
            foreach ($dist in $distributions.DistributionList.Items) {
                $comment = if ($dist.Comment) { $dist.Comment } else { "No comment" }
                Write-Host "   ID: $($dist.Id) | Status: $($dist.Status) | Comment: $comment" -ForegroundColor Cyan
            }
        } else {
            Write-Host "   No distributions found" -ForegroundColor White
        }
    } catch {
        Write-Host "❌ Error listing distributions: $($_.Exception.Message)" -ForegroundColor Red
    }
}