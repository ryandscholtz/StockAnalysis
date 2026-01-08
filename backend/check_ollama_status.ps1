# Comprehensive Ollama Status Check
param(
    [string]$Profile = "Cerebrum",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$Region = "us-east-1",
    [string]$OllamaIP = "52.0.231.150"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ollama EC2 Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check EC2 Instance Status
Write-Host "1. EC2 Instance Status:" -ForegroundColor Yellow
$instance = aws ec2 describe-instances --instance-ids $InstanceId --profile $Profile --region $Region --query "Reservations[0].Instances[0]" --output json 2>&1 | ConvertFrom-Json

if ($instance) {
    $state = $instance.State.Name
    $ip = $instance.PublicIpAddress
    $instanceType = $instance.InstanceType
    
    Write-Host "   State: $state" -ForegroundColor $(if ($state -eq "running") { "Green" } else { "Red" })
    Write-Host "   Public IP: $ip" -ForegroundColor Cyan
    Write-Host "   Instance Type: $instanceType" -ForegroundColor White
    
    if ($ip -eq $OllamaIP) {
        Write-Host "   Elastic IP: Correctly associated" -ForegroundColor Green
    } else {
        Write-Host "   Elastic IP: MISMATCH! Expected $OllamaIP, got $ip" -ForegroundColor Red
    }
    
    if ($state -ne "running") {
        Write-Host ""
        Write-Host "   WARNING: Instance is not running. Starting..." -ForegroundColor Yellow
        aws ec2 start-instances --instance-ids $InstanceId --profile $Profile --region $Region | Out-Null
        Write-Host "   Waiting for instance to start..." -ForegroundColor Cyan
        aws ec2 wait instance-running --instance-ids $InstanceId --profile $Profile --region $Region
        Start-Sleep -Seconds 10
        Write-Host "   OK: Instance started" -ForegroundColor Green
    }
} else {
    Write-Host "   ERROR: Failed to get instance information" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. Check Security Group
Write-Host "2. Security Group (Port 11434):" -ForegroundColor Yellow
$sgId = $instance.SecurityGroups[0].GroupId
$sgRules = aws ec2 describe-security-groups --group-ids $sgId --profile $Profile --region $Region --query "SecurityGroups[0].IpPermissions" --output json | ConvertFrom-Json

$port11434Open = $false
foreach ($rule in $sgRules) {
    if ($rule.FromPort -eq 11434 -or ($rule.FromPort -le 11434 -and $rule.ToPort -ge 11434)) {
        $port11434Open = $true
        Write-Host "   Port 11434: OPEN" -ForegroundColor Green
        break
    }
}

if (-not $port11434Open) {
    Write-Host "   Port 11434: CLOSED or restricted" -ForegroundColor Red
    Write-Host "   Opening port 11434..." -ForegroundColor Yellow
    aws ec2 authorize-security-group-ingress --group-id $sgId --protocol tcp --port 11434 --cidr "0.0.0.0/0" --profile $Profile --region $Region 2>&1 | Out-Null
    Write-Host "   OK: Port 11434 opened" -ForegroundColor Green
}

Write-Host ""

# 3. Test Ollama Connectivity
Write-Host "3. Ollama Connectivity:" -ForegroundColor Yellow
$ollamaUrl = "http://" + $OllamaIP + ":11434/api/tags"
Write-Host "   Testing: $ollamaUrl" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri $ollamaUrl -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "   OK: Ollama is accessible!" -ForegroundColor Green
    
    $json = $response.Content | ConvertFrom-Json
    if ($json.models) {
        Write-Host "   Available models:" -ForegroundColor Cyan
        foreach ($model in $json.models) {
            $modelName = $model.name
            $hasVision = if ($modelName -like "*vision*") { " (vision)" } else { "" }
            Write-Host "     - $modelName$hasVision" -ForegroundColor White
        }
        
        $hasCorrectModel = $json.models | Where-Object { $_.name -eq "llama3.2-vision:11b" }
        if ($hasCorrectModel) {
            Write-Host "   OK: Required model (llama3.2-vision:11b) is available" -ForegroundColor Green
        } else {
            Write-Host "   WARNING: Required model (llama3.2-vision:11b) is NOT available" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "   ERROR: Ollama is NOT accessible" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Next steps:" -ForegroundColor Cyan
    Write-Host "   1. SSH into EC2: ssh -i your-key.pem ec2-user@$OllamaIP" -ForegroundColor White
    Write-Host "   2. Start Ollama: sudo systemctl start ollama" -ForegroundColor White
    Write-Host "   3. Enable auto-start: sudo systemctl enable ollama" -ForegroundColor White
    Write-Host "   4. Check status: sudo systemctl status ollama" -ForegroundColor White
}

Write-Host ""

# 4. Check .env Configuration
Write-Host "4. Backend Configuration:" -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    $llamaUrl = if ($envContent -match "LLAMA_API_URL=(.+)") { $matches[1].Trim() } else { "NOT SET" }
    $llamaModel = if ($envContent -match "LLAMA_MODEL=(.+)") { $matches[1].Trim() } else { "NOT SET" }
    $autoStop = if ($envContent -match "EC2_AUTO_STOP=(.+)") { $matches[1].Trim() } else { "NOT SET" }
    
    Write-Host "   LLAMA_API_URL: $llamaUrl" -ForegroundColor $(if ($llamaUrl -eq "http://$OllamaIP:11434") { "Green" } else { "Yellow" })
    Write-Host "   LLAMA_MODEL: $llamaModel" -ForegroundColor $(if ($llamaModel -eq "llama3.2-vision:11b") { "Green" } else { "Yellow" })
    Write-Host "   EC2_AUTO_STOP: $autoStop" -ForegroundColor $(if ($autoStop -eq "false") { "Green" } else { "Yellow" })
} else {
    Write-Host "   ERROR: .env file not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($state -eq "running" -and $port11434Open) {
    try {
        $testUrl = "http://" + $OllamaIP + ":11434/api/tags"
        $test = Invoke-WebRequest -Uri $testUrl -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "OK: Everything is configured correctly!" -ForegroundColor Green
        Write-Host "  Ollama should be working now." -ForegroundColor Green
    } catch {
        Write-Host "WARNING: Configuration is correct, but Ollama service is not running." -ForegroundColor Yellow
        Write-Host "  You need to SSH into EC2 and start Ollama manually." -ForegroundColor Yellow
    }
} else {
    Write-Host "WARNING: Some configuration issues detected. See details above." -ForegroundColor Yellow
}
