# Check and start Ollama on EC2 instance
param(
    [string]$Profile = "Cerebrum",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$Region = "us-east-1",
    [string]$KeyFile = ""
)

Write-Host "Checking Ollama on EC2 instance..." -ForegroundColor Cyan
Write-Host ""

# Get instance IP
$instanceInfo = aws ec2 describe-instances --instance-ids $InstanceId --profile $Profile --region $Region --query "Reservations[0].Instances[0].[State.Name,PublicIpAddress]" --output text
$parts = $instanceInfo -split "`t"
$state = $parts[0].Trim()
$ip = if ($parts.Count -gt 1) { $parts[1].Trim() } else { "" }

if ($state -ne "running") {
    Write-Host "Instance is not running (state: $state)" -ForegroundColor Red
    exit 1
}

Write-Host "Instance IP: $ip" -ForegroundColor Cyan
Write-Host ""

# Test Ollama connectivity
Write-Host "Testing Ollama connectivity..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://$ip:11434/api/tags" -TimeoutSec 5 -UseBasicParsing
    Write-Host "Ollama is accessible!" -ForegroundColor Green
    $json = $response.Content | ConvertFrom-Json
    if ($json.models) {
        Write-Host "Available models:" -ForegroundColor Cyan
        $json.models | ForEach-Object { Write-Host "  - $($_.name)" -ForegroundColor White }
    }
    exit 0
} catch {
    Write-Host "Ollama is NOT accessible" -ForegroundColor Red
    Write-Host ""
}

# If not accessible and key file provided, try to start Ollama
if ($KeyFile -and (Test-Path $KeyFile)) {
    Write-Host "Attempting to start Ollama via SSH..." -ForegroundColor Yellow
    Write-Host "SSH command:" -ForegroundColor Cyan
    Write-Host "  ssh -i $KeyFile ec2-user@$ip" -ForegroundColor White
    Write-Host ""
    Write-Host "Once connected, run:" -ForegroundColor Cyan
    Write-Host "  sudo systemctl status ollama" -ForegroundColor White
    Write-Host "  sudo systemctl start ollama" -ForegroundColor White
    Write-Host "  sudo systemctl enable ollama" -ForegroundColor White
    Write-Host "  curl http://localhost:11434/api/tags" -ForegroundColor White
} else {
    Write-Host "To start Ollama, SSH into the instance:" -ForegroundColor Yellow
    Write-Host "  ssh -i your-key.pem ec2-user@$ip" -ForegroundColor White
    Write-Host ""
    Write-Host "Then run:" -ForegroundColor Cyan
    Write-Host "  sudo systemctl start ollama" -ForegroundColor White
    Write-Host "  sudo systemctl enable ollama" -ForegroundColor White
}

