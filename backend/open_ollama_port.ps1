# Open port 11434 in EC2 security group for Ollama
param(
    [string]$Profile = "Cerebrum",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$Region = "us-east-1"
)

Write-Host "Opening port 11434 for Ollama..." -ForegroundColor Cyan

# Get security group ID
$sgId = aws ec2 describe-instances --instance-ids $InstanceId --profile $Profile --region $Region --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" --output text

if (-not $sgId) {
    Write-Host "Error: Could not find security group for instance" -ForegroundColor Red
    exit 1
}

Write-Host "Security Group: $sgId" -ForegroundColor White

# Check if port is already open
$sgInfo = aws ec2 describe-security-groups --group-ids $sgId --profile $Profile --region $Region --output json | ConvertFrom-Json
$port11434 = $sgInfo.SecurityGroups[0].IpPermissions | Where-Object { $_.FromPort -eq 11434 -or $_.ToPort -eq 11434 }

if ($port11434) {
    Write-Host "Port 11434 is already open!" -ForegroundColor Green
    exit 0
}

# Add inbound rule for port 11434
Write-Host "Adding inbound rule for port 11434..." -ForegroundColor Yellow
$result = aws ec2 authorize-security-group-ingress `
    --group-id $sgId `
    --protocol tcp `
    --port 11434 `
    --cidr 0.0.0.0/0 `
    --profile $Profile `
    --region $Region `
    --output json 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Port 11434 opened successfully!" -ForegroundColor Green
    Write-Host "Ollama should now be accessible from anywhere" -ForegroundColor Cyan
} else {
    if ($result -match "already exists") {
        Write-Host "Port 11434 is already open (rule may have been added manually)" -ForegroundColor Yellow
    } else {
        Write-Host "Failed to open port 11434" -ForegroundColor Red
        Write-Host $result
        exit 1
    }
}

