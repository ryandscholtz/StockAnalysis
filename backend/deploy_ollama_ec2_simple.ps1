# Deploy Ollama on AWS EC2 - Simplified Version
param(
    [string]$Profile = "Cerebrum",
    [string]$Region = "eu-west-1",
    [string]$InstanceType = "g4dn.xlarge"
)

Write-Host "🚀 Deploying Ollama on AWS EC2..." -ForegroundColor Green
Write-Host "Profile: $Profile, Region: $Region, Instance: $InstanceType" -ForegroundColor Cyan

# Verify AWS credentials
Write-Host "`n📋 Verifying AWS credentials..." -ForegroundColor Yellow
$identity = aws sts get-caller-identity --profile $Profile 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ AWS credentials not configured. Run: aws configure --profile $Profile" -ForegroundColor Red
    exit 1
}
Write-Host "✓ AWS credentials verified" -ForegroundColor Green

# Create key pair if needed
$KeyPairName = "ollama-keypair"
Write-Host "`n🔑 Checking key pair..." -ForegroundColor Yellow
$keyCheck = aws ec2 describe-key-pairs --profile $Profile --region $Region --key-names $KeyPairName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating key pair: $KeyPairName" -ForegroundColor Cyan
    $keyOutput = aws ec2 create-key-pair --profile $Profile --region $Region --key-name $KeyPairName --query 'KeyMaterial' --output text
    if ($keyOutput) {
        $keyOutput | Out-File -FilePath "$KeyPairName.pem" -Encoding ASCII
        Write-Host "✓ Key pair created: $KeyPairName.pem" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create key pair" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Key pair exists: $KeyPairName" -ForegroundColor Green
}

# Get VPC and subnet
Write-Host "`n🌐 Getting VPC information..." -ForegroundColor Yellow
$vpcId = aws ec2 describe-vpcs --profile $Profile --region $Region --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text
$subnetId = aws ec2 describe-subnets --profile $Profile --region $Region --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[0].SubnetId" --output text
Write-Host "✓ VPC: $vpcId, Subnet: $subnetId" -ForegroundColor Green

# Create security group
$SecurityGroupName = "ollama-sg"
Write-Host "`n🔒 Setting up security group..." -ForegroundColor Yellow
$sgCheck = aws ec2 describe-security-groups --profile $Profile --region $Region --group-names $SecurityGroupName 2>&1
if ($LASTEXITCODE -ne 0) {
    $sgId = aws ec2 create-security-group --profile $Profile --region $Region --group-name $SecurityGroupName --description "Ollama EC2 Security Group" --vpc-id $vpcId --query 'GroupId' --output text
    $myIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $sgId --protocol tcp --port 22 --cidr "$myIp/32" | Out-Null
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $sgId --protocol tcp --port 11434 --cidr "0.0.0.0/0" | Out-Null
    Write-Host "✓ Security group created: $sgId" -ForegroundColor Green
} else {
    $sgId = aws ec2 describe-security-groups --profile $Profile --region $Region --group-names $SecurityGroupName --query "SecurityGroups[0].GroupId" --output text
    Write-Host "✓ Security group exists: $sgId" -ForegroundColor Green
}

# Get Ubuntu AMI
Write-Host "`n📦 Getting Ubuntu AMI..." -ForegroundColor Yellow
$amiQuery = 'reverse(sort_by(Images, &CreationDate))[0].ImageId'
$amiId = aws ec2 describe-images --profile $Profile --region $Region --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query $amiQuery --output text
Write-Host "✓ AMI: $amiId" -ForegroundColor Green

# Create user data file
$userDataFile = "ollama-userdata.sh"
$userDataContent = @'
#!/bin/bash
set -e
apt-get update -y
apt-get install -y curl
curl -fsSL https://ollama.com/install.sh | sh
export OLLAMA_NUM_PARALLEL=8
export OLLAMA_MAX_LOADED_MODELS=1
ollama pull llama3.2-vision:11b
cat > /etc/systemd/system/ollama.service << 'SERVEOF'
[Unit]
Description=Ollama Service
After=network.target
[Service]
Type=simple
User=root
Environment="OLLAMA_NUM_PARALLEL=8"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
ExecStart=/usr/local/bin/ollama serve --host 0.0.0.0
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
SERVEOF
systemctl daemon-reload
systemctl enable ollama
systemctl start ollama
'@
$userDataContent | Out-File -FilePath $userDataFile -Encoding ASCII -NoNewline

# Encode user data
$userDataBytes = [System.IO.File]::ReadAllBytes($userDataFile)
$userDataBase64 = [Convert]::ToBase64String($userDataBytes)

# Launch instance
Write-Host "`n🚀 Launching EC2 instance..." -ForegroundColor Yellow
$tagSpec = 'ResourceType=instance,Tags=[{Key=Name,Value=ollama-server}]'
$instanceId = aws ec2 run-instances --profile $Profile --region $Region --image-id $amiId --instance-type $InstanceType --key-name $KeyPairName --security-group-ids $sgId --subnet-id $subnetId --user-data $userDataBase64 --tag-specifications $tagSpec --query "Instances[0].InstanceId" --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to launch instance" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Instance launched: $instanceId" -ForegroundColor Green
Write-Host "⏳ Waiting for instance to be running..." -ForegroundColor Yellow
aws ec2 wait instance-running --profile $Profile --region $Region --instance-ids $instanceId

# Get IP addresses
Start-Sleep -Seconds 5
$publicIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $instanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text
$privateIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $instanceId --query "Reservations[0].Instances[0].PrivateIpAddress" --output text

Write-Host "`n✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "`nInstance Details:" -ForegroundColor Cyan
Write-Host "  Instance ID: $instanceId"
Write-Host "  Public IP:   $publicIp"
Write-Host "  Private IP:  $privateIp"
Write-Host "`nOllama URL: http://$publicIp:11434" -ForegroundColor Yellow
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Wait 5-10 minutes for Ollama to install and download model"
Write-Host "2. Test: curl http://$publicIp:11434/api/tags"
Write-Host "3. Update .env: LLAMA_API_URL=http://$publicIp:11434"
Write-Host "`n⚠️  Instance cost: ~`$0.75/hour. Stop when not in use!" -ForegroundColor Yellow

# Save config
$config = @{
    InstanceId = $instanceId
    PublicIP = $publicIp
    PrivateIP = $privateIp
    Region = $Region
    Profile = $Profile
    OllamaURL = "http://$publicIp:11434"
} | ConvertTo-Json
$config | Out-File -FilePath "ollama-ec2-config.json" -Encoding UTF8

