# Downgrade Ollama EC2 Instance to t3.medium for Cost Savings
param(
    [string]$Profile = "Cerebrum",
    [string]$Region = "us-east-1",
    [string]$InstanceId = "i-056dc6971b402f0b2"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "DOWNGRADING TO t3.medium FOR SAVINGS" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Cost Savings:" -ForegroundColor Cyan
Write-Host "  Current (t3.xlarge): `$121/month (24/7)" -ForegroundColor Yellow
Write-Host "  New (t3.medium): `$30/month (24/7)" -ForegroundColor Green
Write-Host "  Savings: `$91/month (`$1,092/year!)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Specs:" -ForegroundColor Cyan
Write-Host "  t3.medium: 2 vCPU, 4GB RAM" -ForegroundColor Yellow
Write-Host "  Performance: 2-4 concurrent requests" -ForegroundColor Yellow
Write-Host "  Note: Will use swap space for model (slightly slower, but works)" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Continue with downgrade? (y/n)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled" -ForegroundColor Yellow
    exit 0
}

# Stop instance first
Write-Host "`nStopping instance..." -ForegroundColor Yellow
aws ec2 stop-instances --profile $Profile --region $Region --instance-ids $InstanceId
Write-Host "Waiting for instance to stop..." -ForegroundColor Cyan
aws ec2 wait instance-stopped --profile $Profile --region $Region --instance-ids $InstanceId
Write-Host "✓ Instance stopped" -ForegroundColor Green

# Modify instance type
Write-Host "`nModifying instance type to t3.medium..." -ForegroundColor Yellow
aws ec2 modify-instance-attribute --profile $Profile --region $Region --instance-id $InstanceId --instance-type Value=t3.medium
Write-Host "✓ Instance type modified" -ForegroundColor Green

# Start instance
Write-Host "`nStarting instance..." -ForegroundColor Yellow
aws ec2 start-instances --profile $Profile --region $Region --instance-ids $InstanceId
Write-Host "Waiting for instance to start..." -ForegroundColor Cyan
aws ec2 wait instance-running --profile $Profile --region $Region --instance-ids $InstanceId
Write-Host "✓ Instance started" -ForegroundColor Green

# Get new IP (may have changed)
Start-Sleep -Seconds 5
$publicIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text
$instanceType = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].InstanceType" --output text

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "DOWNGRADE COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Instance Details:" -ForegroundColor Cyan
Write-Host "  Instance ID: $InstanceId"
Write-Host "  Instance Type: $instanceType (DOWNGRADED)"
Write-Host "  vCPUs: 2 (was 4)"
Write-Host "  RAM: 4GB (was 16GB)"
Write-Host "  Public IP: $publicIp"
Write-Host "  Ollama URL: http://$publicIp:11434"
Write-Host ""
Write-Host "Cost:" -ForegroundColor Green
Write-Host "  Monthly (24/7): ~`$30.40" -ForegroundColor Cyan
Write-Host "  Annual: ~`$365" -ForegroundColor Cyan
Write-Host "  Savings vs xlarge: `$91/month (`$1,092/year)" -ForegroundColor Green
Write-Host ""
Write-Host "Performance:" -ForegroundColor Yellow
Write-Host "  Can handle: 2-4 concurrent requests"
Write-Host "  Note: Model will use swap space (slightly slower, but functional)"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "  1. Wait 2-3 minutes for Ollama to be ready"
Write-Host "  2. Test: curl http://$publicIp:11434/api/tags"
Write-Host "  3. Update .env if IP changed: LLAMA_API_URL=http://$publicIp:11434"
Write-Host "  4. You can now leave it running 24/7 at `$30/month!" -ForegroundColor Cyan

