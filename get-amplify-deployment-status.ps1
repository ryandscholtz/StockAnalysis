# Get AWS Amplify Deployment Status and Logs
# ARN: arn:aws:amplify:eu-west-1:295202642810:apps/d1h3822e5hvb4m

$appId = "d1h3822e5hvb4m"
$region = "eu-west-1"
$branchName = "main"

Write-Host "Checking Amplify deployment status..." -ForegroundColor Green

# Try to get recent jobs
Write-Host "Getting recent deployment jobs..." -ForegroundColor Yellow
try {
    $jobs = aws amplify list-jobs --app-id $appId --branch-name $branchName --region $region --max-results 5 2>$null
    if ($LASTEXITCODE -eq 0) {
        $jobsData = $jobs | ConvertFrom-Json
        Write-Host "Recent jobs found:" -ForegroundColor Green
        
        foreach ($job in $jobsData.jobSummaries) {
            Write-Host "- Job ID: $($job.jobId)" -ForegroundColor Cyan
            Write-Host "  Status: $($job.status)" -ForegroundColor Cyan
            Write-Host "  Type: $($job.jobType)" -ForegroundColor Cyan
            Write-Host "  Created: $($job.createTime)" -ForegroundColor Cyan
            Write-Host "  Updated: $($job.endTime)" -ForegroundColor Cyan
            Write-Host ""
        }
        
        # Get details for the most recent job
        if ($jobsData.jobSummaries.Count -gt 0) {
            $latestJobId = $jobsData.jobSummaries[0].jobId
            Write-Host "Getting details for latest job: $latestJobId" -ForegroundColor Yellow
            
            $jobDetails = aws amplify get-job --app-id $appId --branch-name $branchName --job-id $latestJobId --region $region 2>$null
            if ($LASTEXITCODE -eq 0) {
                $jobData = $jobDetails | ConvertFrom-Json
                Write-Host "Job Details:" -ForegroundColor Green
                Write-Host "- Status: $($jobData.job.summary.status)" -ForegroundColor Cyan
                Write-Host "- Job Type: $($jobData.job.summary.jobType)" -ForegroundColor Cyan
                Write-Host "- Commit ID: $($jobData.job.summary.commitId)" -ForegroundColor Cyan
                Write-Host "- Commit Message: $($jobData.job.summary.commitMessage)" -ForegroundColor Cyan
                
                if ($jobData.job.steps) {
                    Write-Host "Build Steps:" -ForegroundColor Yellow
                    foreach ($step in $jobData.job.steps) {
                        Write-Host "- $($step.stepName): $($step.status)" -ForegroundColor Cyan
                        if ($step.logUrl) {
                            Write-Host "  Log URL: $($step.logUrl)" -ForegroundColor White
                        }
                    }
                }
            }
        }
    } else {
        Write-Host "Failed to get jobs. AWS CLI might not be configured." -ForegroundColor Red
        Write-Host "Please run 'aws configure' to set up your credentials." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error getting deployment status: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Direct Console Links:" -ForegroundColor Yellow
Write-Host "- App Console: https://$region.console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
Write-Host "- Deployments: https://$region.console.aws.amazon.com/amplify/home?region=$region#/$appId/YnJhbmNoZXM/main" -ForegroundColor Cyan