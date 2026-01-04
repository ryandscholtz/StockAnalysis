# Minimal Ollama EC2 Deployment Script
param(
    [string]$Profile = "Cerebrum",
    [string]$Region = "eu-west-1",
    [string]$InstanceType = "g4dn.xlarge"
)

Write-Host "Deploying Ollama on AWS EC2..." -ForegroundColor Green
Write-Host "Profile: $Profile, Region: $Region" -ForegroundColor Cyan

# Verify credentials
$identity = aws sts get-caller-identity --profile $Profile 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: AWS credentials not configured" -ForegroundColor Red
    exit 1
}
Write-Host "AWS credentials verified" -ForegroundColor Green

# Key pair
$KeyPairName = "ollama-keypair"
$keyCheck = aws ec2 describe-key-pairs --profile $Profile --region $Region --key-names $KeyPairName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating key pair..." -ForegroundColor Cyan
    $keyOutput = aws ec2 create-key-pair --profile $Profile --region $Region --key-name $KeyPairName --query 'KeyMaterial' --output text
    if ($keyOutput) {
        $keyOutput | Out-File -FilePath "$KeyPairName.pem" -Encoding ASCII
        Write-Host "Key pair created: $KeyPairName.pem" -ForegroundColor Green
    }
}

# VPC and subnet
$vpcId = aws ec2 describe-vpcs --profile $Profile --region $Region --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text
$subnetId = aws ec2 describe-subnets --profile $Profile --region $Region --filters "Name=vpc-id,Values=$vpcId" --query "Subnets[0].SubnetId" --output text
Write-Host "VPC: $vpcId, Subnet: $subnetId" -ForegroundColor Green

# Security group
$SecurityGroupName = "ollama-sg"
$sgCheck = aws ec2 describe-security-groups --profile $Profile --region $Region --group-names $SecurityGroupName 2>&1
if ($LASTEXITCODE -ne 0) {
    $sgId = aws ec2 create-security-group --profile $Profile --region $Region --group-name $SecurityGroupName --description "Ollama EC2" --vpc-id $vpcId --query 'GroupId' --output text
    $myIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $sgId --protocol tcp --port 22 --cidr "$myIp/32" | Out-Null
    aws ec2 authorize-security-group-ingress --profile $Profile --region $Region --group-id $sgId --protocol tcp --port 11434 --cidr "0.0.0.0/0" | Out-Null
    Write-Host "Security group created: $sgId" -ForegroundColor Green
} else {
    $sgId = aws ec2 describe-security-groups --profile $Profile --region $Region --group-names $SecurityGroupName --query "SecurityGroups[0].GroupId" --output text
    Write-Host "Security group exists: $sgId" -ForegroundColor Green
}

# Get AMI
Write-Host "Getting Ubuntu AMI..." -ForegroundColor Yellow
$amiId = aws ec2 describe-images --profile $Profile --region $Region --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query "Images[-1].ImageId" --output text
Write-Host "AMI: $amiId" -ForegroundColor Green

# User data
$userDataScript = "#!/bin/bash`napt-get update -y`napt-get install -y curl`ncurl -fsSL https://ollama.com/install.sh | sh`nexport OLLAMA_NUM_PARALLEL=8`nexport OLLAMA_MAX_LOADED_MODELS=1`nollama pull llama3.2-vision:11b`necho '[Unit]' > /etc/systemd/system/ollama.service`necho 'Description=Ollama Service' >> /etc/systemd/system/ollama.service`necho 'After=network.target' >> /etc/systemd/system/ollama.service`necho '[Service]' >> /etc/systemd/system/ollama.service`necho 'Type=simple' >> /etc/systemd/system/ollama.service`necho 'User=root' >> /etc/systemd/system/ollama.service`necho 'Environment=`"OLLAMA_NUM_PARALLEL=8`"' >> /etc/systemd/system/ollama.service`necho 'Environment=`"OLLAMA_MAX_LOADED_MODELS=1`"' >> /etc/systemd/system/ollama.service`necho 'ExecStart=/usr/local/bin/ollama serve --host 0.0.0.0' >> /etc/systemd/system/ollama.service`necho 'Restart=always' >> /etc/systemd/system/ollama.service`necho '[Install]' >> /etc/systemd/system/ollama.service`necho 'WantedBy=multi-user.target' >> /etc/systemd/system/ollama.service`nsystemctl daemon-reload`nsystemctl enable ollama`nsystemctl start ollama`n"
$userDataBytes = [System.Text.Encoding]::UTF8.GetBytes($userDataScript)
$userDataBase64 = [Convert]::ToBase64String($userDataBytes)

# Launch instance
Write-Host "Launching EC2 instance..." -ForegroundColor Yellow
$tagSpec = 'ResourceType=instance,Tags=[{Key=Name,Value=ollama-server}]'
$instanceId = aws ec2 run-instances --profile $Profile --region $Region --image-id $amiId --instance-type $InstanceType --key-name $KeyPairName --security-group-ids $sgId --subnet-id $subnetId --user-data $userDataBase64 --tag-specifications $tagSpec --query "Instances[0].InstanceId" --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to launch instance" -ForegroundColor Red
    exit 1
}

Write-Host "Instance launched: $instanceId" -ForegroundColor Green
Write-Host "Waiting for instance to be running..." -ForegroundColor Yellow
aws ec2 wait instance-running --profile $Profile --region $Region --instance-ids $instanceId

# Get IPs
Start-Sleep -Seconds 5
$publicIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $instanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text
$privateIp = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $instanceId --query "Reservations[0].Instances[0].PrivateIpAddress" --output text

Write-Host "`nDEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "Instance ID: $instanceId"
Write-Host "Public IP: $publicIp"
Write-Host "Private IP: $privateIp"
Write-Host "Ollama URL: http://$publicIp:11434" -ForegroundColor Yellow
Write-Host "`nNext: Wait 5-10 min, then test: curl http://$publicIp:11434/api/tags"
Write-Host "Update .env: LLAMA_API_URL=http://$publicIp:11434"

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

