# Setup EC2 Auto-Start for Ollama Processing
# This enables automatic instance startup when PDF processing is needed

param(
    [string]$Profile = "Cerebrum",
    [string]$Region = "us-east-1",
    [string]$InstanceId = "i-056dc6971b402f0b2"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "EC2 AUTO-START SETUP" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "This will configure your backend to automatically start the EC2 instance"
Write-Host "when PDF processing is needed, saving costs when idle."
Write-Host ""

# Check if boto3 is installed
Write-Host "Checking Python dependencies..." -ForegroundColor Yellow
$pythonCmd = "python"
if (Test-Path "venv\Scripts\python.exe") {
    $pythonCmd = "venv\Scripts\python.exe"
}

$boto3Check = & $pythonCmd -c "import boto3; print('ok')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing boto3..." -ForegroundColor Yellow
    & $pythonCmd -m pip install boto3
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install boto3" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ boto3 is installed" -ForegroundColor Green

# Update .env file
Write-Host "`nUpdating .env file..." -ForegroundColor Yellow
$envFile = ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    New-Item -Path $envFile -ItemType File | Out-Null
}

# Read current .env
$envContent = Get-Content $envFile -ErrorAction SilentlyContinue

# Update or add EC2 settings
$newLines = @()
$foundEc2AutoStart = $false
$foundInstanceId = $false
$foundAwsProfile = $false
$foundAwsRegion = $false

foreach ($line in $envContent) {
    if ($line -match "^EC2_AUTO_START=") {
        $newLines += "EC2_AUTO_START=true"
        $foundEc2AutoStart = $true
    } elseif ($line -match "^OLLAMA_EC2_INSTANCE_ID=") {
        $newLines += "OLLAMA_EC2_INSTANCE_ID=$InstanceId"
        $foundInstanceId = $true
    } elseif ($line -match "^AWS_PROFILE=") {
        $newLines += "AWS_PROFILE=$Profile"
        $foundAwsProfile = $true
    } elseif ($line -match "^AWS_REGION=") {
        $newLines += "AWS_REGION=$Region"
        $foundAwsRegion = $true
    } else {
        $newLines += $line
    }
}

# Add missing settings
if (-not $foundEc2AutoStart) {
    $newLines += "EC2_AUTO_START=true"
}
if (-not $foundInstanceId) {
    $newLines += "OLLAMA_EC2_INSTANCE_ID=$InstanceId"
}
if (-not $foundAwsProfile) {
    $newLines += "AWS_PROFILE=$Profile"
}
if (-not $foundAwsRegion) {
    $newLines += "AWS_REGION=$Region"
}

# Optional settings
if (-not ($envContent -match "EC2_STARTUP_WAIT_SECONDS")) {
    $newLines += "EC2_STARTUP_WAIT_SECONDS=120"
}
if (-not ($envContent -match "EC2_AUTO_SHUTDOWN_MINUTES")) {
    $newLines += "EC2_AUTO_SHUTDOWN_MINUTES=15"
}

# Write updated .env
$newLines | Set-Content $envFile
Write-Host "✓ .env file updated" -ForegroundColor Green

# Get current instance IP
Write-Host "`nGetting current instance IP..." -ForegroundColor Yellow
$currentState = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
$currentIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text

if ($currentState -eq "running" -and $currentIp) {
    Write-Host "Current IP: $currentIp" -ForegroundColor Cyan
    Write-Host "Updating LLAMA_API_URL in .env..." -ForegroundColor Yellow
    
    # Update LLAMA_API_URL
    $envContent = Get-Content $envFile
    $updated = $false
    $newEnvContent = @()
    foreach ($line in $envContent) {
        if ($line -match "^LLAMA_API_URL=") {
            $newEnvContent += "LLAMA_API_URL=http://$currentIp:11434"
            $updated = $true
        } else {
            $newEnvContent += $line
        }
    }
    if (-not $updated) {
        $newEnvContent += "LLAMA_API_URL=http://$currentIp:11434"
    }
    $newEnvContent | Set-Content $envFile
    Write-Host "✓ LLAMA_API_URL updated" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  EC2 Auto-Start: ENABLED"
Write-Host "  Instance ID: $InstanceId"
Write-Host "  AWS Profile: $Profile"
Write-Host "  AWS Region: $Region"
Write-Host ""
Write-Host "How it works:" -ForegroundColor Yellow
Write-Host "  1. When you upload a PDF, backend checks if EC2 is running"
Write-Host "  2. If stopped, it automatically starts the instance"
Write-Host "  3. Waits for instance to be ready (~2 minutes)"
Write-Host "  4. Processes the PDF"
Write-Host "  5. Instance stays running (you can stop manually to save costs)"
Write-Host ""
Write-Host "Cost savings:" -ForegroundColor Green
Write-Host "  - Instance only runs when processing PDFs"
Write-Host "  - Stop manually after processing: ~`$0.10/month (storage only)"
Write-Host "  - Or leave running: ~`$30/month (t3.medium) or ~`$121/month (t3.xlarge)"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart your backend server"
Write-Host "  2. Upload a PDF - instance will auto-start if needed!"
Write-Host "  3. After processing, stop instance manually to save costs"
