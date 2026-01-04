# Manage Ollama EC2 Instance - Start/Stop/Status
param(
    [string]$Action = "status",
    [string]$Profile = "Cerebrum",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$Region = "us-east-1"
)

Write-Host "Managing Ollama EC2 Instance..." -ForegroundColor Green
Write-Host "Instance ID: $InstanceId" -ForegroundColor Cyan

if ($Action -eq "stop") {
    Write-Host "`nStopping instance to save costs..." -ForegroundColor Yellow
    aws ec2 stop-instances --instance-ids $InstanceId --profile $Profile --region $Region
    Write-Host "✓ Instance stopping. You're no longer being charged for compute!" -ForegroundColor Green
    Write-Host "  (Only paying for storage: ~`$0.10/month)" -ForegroundColor Cyan
    
} elseif ($Action -eq "start") {
    Write-Host "`nStarting instance..." -ForegroundColor Yellow
    aws ec2 start-instances --instance-ids $InstanceId --profile $Profile --region $Region
    Write-Host "Waiting for instance to be ready..." -ForegroundColor Cyan
    aws ec2 wait instance-running --profile $Profile --region $Region --instance-ids $InstanceId
    
    Start-Sleep -Seconds 5
    $ip = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text
    $instanceType = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].InstanceType" --output text
    
    Write-Host "`n✓ Instance started!" -ForegroundColor Green
    Write-Host "  Instance Type: $instanceType" -ForegroundColor Cyan
    Write-Host "  Public IP: $ip" -ForegroundColor Cyan
    Write-Host "  Ollama URL: http://$ip:11434" -ForegroundColor Yellow
    Write-Host "`n⚠️  Instance is now running and incurring costs (~`$0.17/hour)" -ForegroundColor Yellow
    Write-Host "  Remember to stop it when done: .\manage_ollama_instance.ps1 stop" -ForegroundColor Cyan
    
} else {
    $state = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
    $instanceType = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].InstanceType" --output text
    
    Write-Host "`nInstance Status:" -ForegroundColor Cyan
    Write-Host "  State: $state" -ForegroundColor $(if ($state -eq "running") { "Green" } else { "Yellow" })
    Write-Host "  Type: $instanceType"
    
    if ($state -eq "running") {
        $ip = aws ec2 describe-instances --profile $Profile --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text
        Write-Host "  Public IP: $ip"
        Write-Host "  Ollama URL: http://$ip:11434" -ForegroundColor Yellow
        Write-Host "`n⚠️  Instance is running - you're being charged ~`$0.17/hour" -ForegroundColor Yellow
        Write-Host "  Stop it: .\manage_ollama_instance.ps1 stop" -ForegroundColor Cyan
    } else {
        Write-Host "`n✓ Instance is stopped - no compute charges" -ForegroundColor Green
        Write-Host "  Start it: .\manage_ollama_instance.ps1 start" -ForegroundColor Cyan
    }
}
