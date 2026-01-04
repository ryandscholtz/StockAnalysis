# Deploy Ollama on AWS EC2
# This script creates an EC2 instance with Ollama pre-configured for concurrent processing

param(
    [string]$Profile = "Cerebrum",
    [string]$Region = "eu-west-1",
    [string]$InstanceType = "g4dn.xlarge",  # GPU instance (change to c5.2xlarge for CPU-only)
    [string]$KeyPairName = "ollama-keypair",
    [string]$SecurityGroupName = "ollama-sg"
)

Write-Host "🚀 Deploying Ollama on AWS EC2..." -ForegroundColor Green
Write-Host "Profile: $Profile" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host "Instance Type: $InstanceType" -ForegroundColor Cyan

# Check if AWS CLI is configured
Write-Host "`n📋 Verifying AWS credentials..." -ForegroundColor Yellow
$identity = aws sts get-caller-identity --profile $Profile 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: AWS credentials not configured for profile '$Profile'" -ForegroundColor Red
    Write-Host "Run: aws configure --profile $Profile" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ AWS credentials verified" -ForegroundColor Green

# Get the account ID
$accountId = (aws sts get-caller-identity --profile $Profile --query Account --output text)
Write-Host "Account ID: $accountId" -ForegroundColor Cyan

# Create or get key pair
Write-Host "`n🔑 Setting up SSH key pair..." -ForegroundColor Yellow
$keyExists = aws ec2 describe-key-pairs --profile $Profile --region $Region --key-names $KeyPairName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating new key pair: $KeyPairName" -ForegroundColor Cyan
    aws ec2 create-key-pair --profile $Profile --region $Region --key-name $KeyPairName --query 'KeyMaterial' --output text > "$KeyPairName.pem"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Key pair created. Saved to: $KeyPairName.pem" -ForegroundColor Green
        Write-Host "⚠️  IMPORTANT: Keep this file secure! You'll need it to SSH into the instance." -ForegroundColor Yellow
        # Set proper permissions (Unix-like)
        icacls "$KeyPairName.pem" /inheritance:r /grant:r "$env:USERNAME:R"
    } else {
        Write-Host "❌ Failed to create key pair" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Key pair already exists: $KeyPairName" -ForegroundColor Green
}

# Get default VPC
Write-Host "`n🌐 Getting VPC information..." -ForegroundColor Yellow
$vpcId = aws ec2 describe-vpcs --profile $Profile --region $Region --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text
if (-not $vpcId -or $vpcId -eq "None") {
    Write-Host "❌ No default VPC found. Please create a VPC first." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Using VPC: $vpcId" -ForegroundColor Green

# Get default subnet
$subnetId = aws ec2 describe-subnets --profile $Profile --region $Region --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[0].SubnetId" --output text
Write-Host "✓ Using Subnet: $subnetId" -ForegroundColor Green

# Create security group
Write-Host "`n🔒 Creating security group..." -ForegroundColor Yellow
$sgExists = aws ec2 describe-security-groups --profile $Profile --region $Region --group-names $SecurityGroupName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating security group: $SecurityGroupName" -ForegroundColor Cyan
    $sgId = aws ec2 create-security-group --profile $Profile --region $Region --group-name $SecurityGroupName --description "Security group for Ollama EC2 instance" --vpc-id $vpcId --query 'GroupId' --output text
    
    # Allow SSH (port 22) from your IP
    Write-Host "Getting your public IP..." -ForegroundColor Cyan
    $myIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
    Write-Host "Your IP: $myIp" -ForegroundColor Cyan
    
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $sgId --protocol tcp --port 22 --cidr "$myIp/32" | Out-Null
    Write-Host "✓ Allowed SSH from your IP ($myIp)" -ForegroundColor Green
    
    # Allow Ollama API (port 11434) from anywhere (you can restrict this later)
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $sgId --protocol tcp --port 11434 --cidr "0.0.0.0/0" | Out-Null
    Write-Host "✓ Allowed Ollama API (port 11434) from anywhere" -ForegroundColor Green
    Write-Host "⚠️  NOTE: Consider restricting port 11434 to your backend IP for better security" -ForegroundColor Yellow
} else {
    $sgId = aws ec2 describe-security-groups --profile $Profile --region $Region --group-names $SecurityGroupName --query "SecurityGroups[0].GroupId" --output text
    Write-Host "✓ Security group already exists: $SecurityGroupName ($sgId)" -ForegroundColor Green
}

# Create user data script for Ollama installation
$userDataScript = @'
#!/bin/bash
set -e

# Update system
apt-get update -y
apt-get upgrade -y

# Install dependencies
apt-get install -y curl wget git build-essential

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the vision model
export OLLAMA_NUM_PARALLEL=8
export OLLAMA_MAX_LOADED_MODELS=1
ollama pull llama3.2-vision:11b

# Create systemd service for Ollama
cat > /etc/systemd/system/ollama.service << 'SERVICEEOF'
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
SERVICEEOF

# Enable and start Ollama service
systemctl daemon-reload
systemctl enable ollama
systemctl start ollama

# Wait for Ollama to be ready
sleep 10
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "Ollama is ready!"
        break
    fi
    echo "Waiting for Ollama to start... ($i/30)"
    sleep 2
done

# Log completion
echo "Ollama installation and setup complete!" >> /var/log/ollama-setup.log
'@

# Encode user data (base64)
$userDataBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($userDataScript))

# Get latest Ubuntu 22.04 AMI
Write-Host "`n📦 Getting latest Ubuntu 22.04 AMI..." -ForegroundColor Yellow
$amiQuery = "Images | sort_by(@, &CreationDate) | [-1].ImageId"
$amiId = aws ec2 describe-images --profile $Profile --region $Region --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query "$amiQuery" --output text
Write-Host "✓ Using AMI: $amiId" -ForegroundColor Green

# Launch EC2 instance
Write-Host "`n🚀 Launching EC2 instance..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Cyan

$tagSpec = "ResourceType=instance,Tags=[{Key=Name,Value=ollama-server},{Key=Purpose,Value=PDF-Processing}]"
$instanceId = aws ec2 run-instances --profile $Profile --region $Region --image-id $amiId --instance-type $InstanceType --key-name $KeyPairName --security-group-ids $sgId --subnet-id $subnetId --user-data $userDataBase64 --tag-specifications $tagSpec --query "Instances[0].InstanceId" --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to launch instance" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Instance launched: $instanceId" -ForegroundColor Green

# Wait for instance to be running
Write-Host "`n⏳ Waiting for instance to be running..." -ForegroundColor Yellow
aws ec2 wait instance-running --profile $Profile --region $Region --instance-ids $instanceId
Write-Host "✓ Instance is running" -ForegroundColor Green

# Get public IP
Write-Host "`n🌐 Getting instance details..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$publicIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $instanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text
$privateIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $instanceId --query "Reservations[0].Instances[0].PrivateIpAddress" --output text

Write-Host "✓ Public IP: $publicIp" -ForegroundColor Green
Write-Host "✓ Private IP: $privateIp" -ForegroundColor Green

# Wait for Ollama to be ready (this takes time for model download)
Write-Host "`n⏳ Waiting for Ollama to be ready (this may take 5-10 minutes for model download)..." -ForegroundColor Yellow
Write-Host "The instance is installing Ollama and downloading the model..." -ForegroundColor Cyan

$maxAttempts = 60
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++
    Write-Host "Checking Ollama status... ($attempt/$maxAttempts)" -ForegroundColor Cyan
    
    try {
        $response = Invoke-WebRequest -Uri "http://$publicIp:11434/api/tags" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            Write-Host "✓ Ollama is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Not ready yet - continue waiting
    }
    
    if ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 10
    }
}

if (-not $ready) {
    Write-Host "⚠️  Ollama may still be installing. Check manually:" -ForegroundColor Yellow
    Write-Host "   SSH: ssh -i $KeyPairName.pem ubuntu@$publicIp" -ForegroundColor Cyan
    Write-Host "   Check logs: sudo journalctl -u ollama -f" -ForegroundColor Cyan
} else {
    Write-Host "✓ Ollama is ready and responding!" -ForegroundColor Green
}

# Save configuration
$config = @{
    InstanceId = $instanceId
    PublicIP = $publicIp
    PrivateIP = $privateIp
    Region = $Region
    Profile = $Profile
    KeyPair = $KeyPairName
    OllamaURL = "http://$publicIp:11434"
    CreatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
} | ConvertTo-Json

$config | Out-File -FilePath "ollama-ec2-config.json" -Encoding UTF8
Write-Host "`n✓ Configuration saved to: ollama-ec2-config.json" -ForegroundColor Green

# Display summary
Write-Host "`n" -NoNewline
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "Instance Details:" -ForegroundColor Cyan
Write-Host "  Instance ID: $instanceId" -ForegroundColor White
Write-Host "  Public IP:   $publicIp" -ForegroundColor White
Write-Host "  Private IP:  $privateIp" -ForegroundColor White
Write-Host "  Region:      $Region" -ForegroundColor White
Write-Host ""
Write-Host "Ollama Configuration:" -ForegroundColor Cyan
Write-Host "  URL:         http://$publicIp:11434" -ForegroundColor White
Write-Host "  Model:       llama3.2-vision:11b" -ForegroundColor White
Write-Host "  Parallel:    8 concurrent requests" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Update your backend .env file:" -ForegroundColor White
Write-Host "   LLAMA_API_URL=http://$publicIp:11434" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Test the connection:" -ForegroundColor White
Write-Host "   curl http://$publicIp:11434/api/tags" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. SSH into the instance (if needed):" -ForegroundColor White
Write-Host "   ssh -i $KeyPairName.pem ubuntu@$publicIp" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Monitor Ollama logs:" -ForegroundColor White
Write-Host "   sudo journalctl -u ollama -f" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "   - Keep your key pair file ($KeyPairName.pem) secure!" -ForegroundColor White
Write-Host "   - Consider restricting port 11434 to your backend IP" -ForegroundColor White
Write-Host "   - Instance will continue running and incur costs (~`$0.75/hour)" -ForegroundColor White
$stopCmd = "aws ec2 stop-instances --instance-ids $instanceId --profile $Profile"
Write-Host "   - Stop the instance when not in use: $stopCmd" -ForegroundColor White
Write-Host ""

