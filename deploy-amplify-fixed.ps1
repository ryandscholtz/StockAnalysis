# Deploy to AWS Amplify with fixed configuration
# App ID: d1h3822e5hvb4m

Write-Host "Starting Amplify deployment with fixed configuration..." -ForegroundColor Green

# Check if we have AWS CLI configured
try {
    $awsIdentity = aws sts get-caller-identity 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "AWS CLI not configured. Please run 'aws configure' first." -ForegroundColor Red
        exit 1
    }
    Write-Host "AWS CLI configured" -ForegroundColor Green
} catch {
    Write-Host "AWS CLI not available. Please install AWS CLI first." -ForegroundColor Red
    exit 1
}

# Verify the amplify.yml configuration
if (Test-Path "amplify.yml") {
    Write-Host "Found amplify.yml in root directory" -ForegroundColor Green
    Get-Content "amplify.yml" | Select-Object -First 10
} else {
    Write-Host "amplify.yml not found in root directory" -ForegroundColor Red
    exit 1
}

# Verify frontend directory structure
if (Test-Path "frontend/package.json") {
    Write-Host "Frontend directory structure looks good" -ForegroundColor Green
} else {
    Write-Host "Frontend directory structure issue" -ForegroundColor Red
    exit 1
}

# Trigger new deployment
Write-Host "Triggering new Amplify deployment..." -ForegroundColor Yellow
try {
    $result = aws amplify start-job --app-id d1h3822e5hvb4m --branch-name main --job-type RELEASE --region eu-west-1
    if ($LASTEXITCODE -eq 0) {
        $jobInfo = $result | ConvertFrom-Json
        $jobId = $jobInfo.jobSummary.jobId
        Write-Host "Deployment started successfully!" -ForegroundColor Green
        Write-Host "Job ID: $jobId" -ForegroundColor Cyan
        Write-Host "Monitor at: https://eu-west-1.console.aws.amazon.com/amplify/home?region=eu-west-1#/d1h3822e5hvb4m/YnJhbmNoZXM/main/deployments/$jobId" -ForegroundColor Cyan
        
        # Wait a moment and check initial status
        Start-Sleep -Seconds 5
        Write-Host "Checking deployment status..." -ForegroundColor Yellow
        $status = aws amplify get-job --app-id d1h3822e5hvb4m --branch-name main --job-id $jobId --region eu-west-1
        if ($LASTEXITCODE -eq 0) {
            $statusInfo = $status | ConvertFrom-Json
            Write-Host "Current Status: $($statusInfo.job.summary.status)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "Failed to start deployment" -ForegroundColor Red
        Write-Host $result
    }
} catch {
    Write-Host "Error triggering deployment: $_" -ForegroundColor Red
}

Write-Host "Deployment script completed!" -ForegroundColor Green