# Setup Elastic IP for Ollama EC2 Instance
param(
    [string]$Profile = "Cerebrum",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$Region = "us-east-1"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "ELASTIC IP SETUP FOR OLLAMA EC2" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if instance exists and get its current state
Write-Host "Checking EC2 instance..." -ForegroundColor Cyan
$instanceInfo = aws ec2 describe-instances --instance-ids $InstanceId --profile $Profile --region $Region --query "Reservations[0].Instances[0].[State.Name,PublicIpAddress]" --output text 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Could not find instance $InstanceId" -ForegroundColor Red
    Write-Host $instanceInfo
    exit 1
}

$parts = $instanceInfo -split "`t"
$state = $parts[0].Trim()
$currentIp = if ($parts.Count -gt 1) { $parts[1].Trim() } else { "" }

Write-Host "Instance State: $state" -ForegroundColor $(if ($state -eq "running") { "Green" } else { "Yellow" })
if ($currentIp) {
    Write-Host "Current IP: $currentIp" -ForegroundColor Cyan
}
Write-Host ""

# Check if instance already has an Elastic IP
Write-Host "Checking for existing Elastic IP..." -ForegroundColor Cyan
$existingEip = aws ec2 describe-addresses --profile $Profile --region $Region --filters "Name=instance-id,Values=$InstanceId" --query "Addresses[0].PublicIp" --output text 2>&1

$elasticIp = $null

if ($existingEip -and $existingEip -ne "None" -and $existingEip.Trim() -ne "") {
    Write-Host "Instance already has Elastic IP: $existingEip" -ForegroundColor Green
    $elasticIp = $existingEip.Trim()
} else {
    # Check if there's an unassociated Elastic IP we can use
    Write-Host "Looking for unassociated Elastic IP..." -ForegroundColor Cyan
    $unassociatedEip = aws ec2 describe-addresses --profile $Profile --region $Region --filters "Name=domain,Values=vpc" "Name=instance-id,Values=" --query "Addresses[0].[AllocationId,PublicIp]" --output text 2>&1
    
    if ($unassociatedEip -and $unassociatedEip -ne "None" -and $unassociatedEip.Trim() -ne "") {
        $eipParts = $unassociatedEip -split "`t"
        $allocationId = $eipParts[0].Trim()
        $elasticIp = $eipParts[1].Trim()
        Write-Host "Found unassociated Elastic IP: $elasticIp" -ForegroundColor Yellow
        Write-Host "Associating with instance..." -ForegroundColor Cyan
        
        # Associate the existing Elastic IP
        aws ec2 associate-address --instance-id $InstanceId --allocation-id $allocationId --profile $Profile --region $Region | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Elastic IP associated successfully" -ForegroundColor Green
        } else {
            Write-Host "Failed to associate Elastic IP" -ForegroundColor Red
            exit 1
        }
    } else {
        # Allocate a new Elastic IP
        Write-Host "Allocating new Elastic IP..." -ForegroundColor Cyan
        $eipResult = aws ec2 allocate-address --domain vpc --profile $Profile --region $Region --output json 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to allocate Elastic IP" -ForegroundColor Red
            Write-Host $eipResult
            exit 1
        }
        
        $eipJson = $eipResult | ConvertFrom-Json
        $allocationId = $eipJson.AllocationId
        $elasticIp = $eipJson.PublicIp
        
        Write-Host "Elastic IP allocated: $elasticIp" -ForegroundColor Green
        
        # Associate with instance (instance must be running)
        if ($state -eq "running") {
            Write-Host "Associating Elastic IP with instance..." -ForegroundColor Cyan
            aws ec2 associate-address --instance-id $InstanceId --allocation-id $allocationId --profile $Profile --region $Region | Out-Null
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Elastic IP associated successfully" -ForegroundColor Green
            } else {
                Write-Host "Failed to associate Elastic IP" -ForegroundColor Red
                Write-Host "Note: You can associate it manually later" -ForegroundColor Yellow
            }
        } else {
            Write-Host "Instance is not running. Elastic IP allocated but not associated." -ForegroundColor Yellow
            Write-Host "Start the instance and run this script again to associate." -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "ELASTIC IP SETUP COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Elastic IP: $elasticIp" -ForegroundColor Cyan
Write-Host "Instance ID: $InstanceId" -ForegroundColor White
Write-Host ""

# Update .env file
Write-Host "Updating .env file..." -ForegroundColor Cyan
$envFile = ".env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    $newContent = $content -replace "LLAMA_API_URL=http://[0-9.]+:11434", "LLAMA_API_URL=http://$elasticIp:11434"
    
    if ($newContent -notmatch "LLAMA_API_URL=") {
        $newContent += "`nLLAMA_API_URL=http://$elasticIp:11434`n"
    }
    
    Set-Content -Path $envFile -Value $newContent -NoNewline
    Write-Host ".env file updated" -ForegroundColor Green
} else {
    Write-Host ".env file not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart backend server to load new IP" -ForegroundColor White
Write-Host "  2. Test Ollama connectivity: curl http://$elasticIp:11434/api/tags" -ForegroundColor White
Write-Host "  3. The IP will now stay the same even after instance stop/start!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Elastic IPs are FREE when attached to a running instance." -ForegroundColor Yellow
Write-Host "      You only pay if the Elastic IP is not associated" -ForegroundColor Yellow
