# Upgrade Ollama EC2 Instance to Support More Concurrent Requests
param(
    [string]$Profile = "Cerebrum",
    [string]$Region = "us-east-1",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$NewInstanceType = "t3.xlarge"  # 4 vCPUs, 16GB RAM - supports 4-8 concurrent
)

Write-Host "Upgrading EC2 instance for better concurrent processing..." -ForegroundColor Green
Write-Host "Current: t3.medium (2 vCPUs)" -ForegroundColor Yellow
Write-Host "Upgrading to: $NewInstanceType" -ForegroundColor Cyan

# Stop instance first
Write-Host "`nStopping instance..." -ForegroundColor Yellow
aws ec2 stop-instances --profile $Profile --region $Region --instance-ids $InstanceId
aws ec2 wait instance-stopped --profile $Profile --region $Region --instance-ids $InstanceId
Write-Host "Instance stopped" -ForegroundColor Green

# Modify instance type
Write-Host "`nModifying instance type to $NewInstanceType..." -ForegroundColor Yellow
aws ec2 modify-instance-attribute --profile $Profile --region $Region --instance-id $InstanceId --instance-type Value=$NewInstanceType
Write-Host "Instance type modified" -ForegroundColor Green

# Start instance
Write-Host "`nStarting instance..." -ForegroundColor Yellow
aws ec2 start-instances --profile $Profile --region $Region --instance-ids $InstanceId
aws ec2 wait instance-running --profile $Profile --region $Region --instance-ids $InstanceId
Write-Host "Instance started" -ForegroundColor Green

# Get new IP (may have changed)
Start-Sleep -Seconds 5
$publicIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text

Write-Host "`nUpgrade Complete!" -ForegroundColor Green
Write-Host "New instance type: $NewInstanceType" -ForegroundColor Cyan
Write-Host "Public IP: $publicIp" -ForegroundColor Cyan
Write-Host "Ollama URL: http://$publicIp:11434" -ForegroundColor Cyan
Write-Host "`nThis instance can now handle 4-8 concurrent requests effectively" -ForegroundColor Green

