# Start Ollama on EC2 Instance
param(
    [string]$Profile = "Cerebrum",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$Region = "us-east-1",
    [string]$KeyPath = "",
    [string]$InstanceIP = "52.0.231.150"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Ollama on EC2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get key pair name
$keyPairName = aws ec2 describe-instances --instance-ids $InstanceId --profile $Profile --region $Region --query "Reservations[0].Instances[0].KeyName" --output text
Write-Host "Key Pair Name: $keyPairName" -ForegroundColor Cyan

# Find key file
if ([string]::IsNullOrEmpty($KeyPath)) {
    $possibleLocations = @(
        "$env:USERPROFILE\.ssh\$keyPairName.pem",
        "$env:USERPROFILE\Downloads\$keyPairName.pem",
        "$PWD\$keyPairName.pem",
        "$PWD\..\$keyPairName.pem",
        "$env:USERPROFILE\.ssh\*.pem"
    )
    
    foreach ($loc in $possibleLocations) {
        if ($loc -like "*`**") {
            $files = Get-ChildItem -Path ($loc -replace '\*.*$','') -Filter "*.pem" -ErrorAction SilentlyContinue
            if ($files) {
                $KeyPath = $files[0].FullName
                Write-Host "Found key: $KeyPath" -ForegroundColor Green
                break
            }
        } elseif (Test-Path $loc) {
            $KeyPath = $loc
            Write-Host "Found key: $KeyPath" -ForegroundColor Green
            break
        }
    }
}

if ([string]::IsNullOrEmpty($KeyPath) -or -not (Test-Path $KeyPath)) {
    Write-Host "ERROR: SSH key file not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please provide the path to your SSH key file:" -ForegroundColor Yellow
    Write-Host "  .\start_ollama_remote.ps1 -KeyPath 'C:\path\to\your-key.pem'" -ForegroundColor White
    Write-Host ""
    Write-Host "Or place your key file in one of these locations:" -ForegroundColor Yellow
    Write-Host "  - $env:USERPROFILE\.ssh\$keyPairName.pem" -ForegroundColor White
    Write-Host "  - $env:USERPROFILE\Downloads\$keyPairName.pem" -ForegroundColor White
    Write-Host "  - Current directory: $keyPairName.pem" -ForegroundColor White
    exit 1
}

# Set correct permissions (if on Windows, this is informational)
Write-Host ""
Write-Host "SSH Key: $KeyPath" -ForegroundColor Green
Write-Host "Instance IP: $InstanceIP" -ForegroundColor Cyan
Write-Host ""

# Check if SSH is available
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $sshPath) {
    Write-Host "ERROR: SSH command not found!" -ForegroundColor Red
    Write-Host "Please install OpenSSH or use WSL/Git Bash" -ForegroundColor Yellow
    exit 1
}

Write-Host "Connecting to EC2 instance..." -ForegroundColor Yellow
Write-Host ""

# Create SSH command
$sshCommand = @"
sudo systemctl start ollama
sudo systemctl enable ollama
sleep 2
systemctl status ollama --no-pager -l
"@

# Try to execute via SSH
Write-Host "Executing commands on remote instance..." -ForegroundColor Cyan
Write-Host ""

try {
    # Use SSH to execute commands
    $sshArgs = @(
        "-i", $KeyPath,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "ec2-user@$InstanceIP",
        $sshCommand
    )
    
    & ssh $sshArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "SUCCESS: Ollama service started!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "WARNING: SSH command completed with exit code $LASTEXITCODE" -ForegroundColor Yellow
    }
} catch {
    Write-Host "ERROR: Failed to execute SSH command" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Cyan
    Write-Host "  ssh -i `"$KeyPath`" ec2-user@$InstanceIP" -ForegroundColor White
    Write-Host "  sudo systemctl start ollama" -ForegroundColor White
    Write-Host "  sudo systemctl enable ollama" -ForegroundColor White
}

Write-Host ""
Write-Host "Testing Ollama connectivity..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

try {
    $response = Invoke-WebRequest -Uri "http://$InstanceIP:11434/api/tags" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "SUCCESS: Ollama is accessible!" -ForegroundColor Green
    $json = $response.Content | ConvertFrom-Json
    if ($json.models) {
        Write-Host "Available models:" -ForegroundColor Cyan
        $json.models | ForEach-Object { Write-Host "  - $($_.name)" -ForegroundColor White }
    }
} catch {
    Write-Host "Ollama is still not accessible. It may need more time to start." -ForegroundColor Yellow
    Write-Host "Wait a minute and test: curl http://$InstanceIP:11434/api/tags" -ForegroundColor Cyan
}

