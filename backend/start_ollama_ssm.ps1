# Start Ollama on EC2 using AWS Systems Manager (SSM)
param(
    [string]$Profile = "Cerebrum",
    [string]$InstanceId = "i-056dc6971b402f0b2",
    [string]$Region = "us-east-1"
)

Write-Host "Starting Ollama on EC2 via SSM..." -ForegroundColor Cyan
Write-Host ""

# Check if instance has SSM agent
Write-Host "Checking SSM agent status..." -ForegroundColor Cyan
$ssmStatus = aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$InstanceId" --profile $Profile --region $Region --query "InstanceInformationList[0].PingStatus" --output text 2>&1

if ($ssmStatus -eq "Online") {
    Write-Host "SSM agent is online - can run commands remotely" -ForegroundColor Green
    Write-Host ""
    
    # Start Ollama service
    Write-Host "Starting Ollama service..." -ForegroundColor Yellow
    $commandId = aws ssm send-command `
        --instance-ids $InstanceId `
        --document-name "AWS-RunShellScript" `
        --parameters "commands=['sudo systemctl start ollama','sudo systemctl enable ollama','sleep 3','systemctl status ollama --no-pager']" `
        --profile $Profile `
        --region $Region `
        --query "Command.CommandId" `
        --output text
    
    if ($commandId) {
        Write-Host "Command sent. Command ID: $commandId" -ForegroundColor Cyan
        Write-Host "Waiting for command to complete..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # Get command output
        $output = aws ssm get-command-invocation `
            --command-id $commandId `
            --instance-id $InstanceId `
            --profile $Profile `
            --region $Region `
            --output json 2>&1 | ConvertFrom-Json
        
        Write-Host ""
        Write-Host "Command Status: $($output.Status)" -ForegroundColor $(if ($output.Status -eq "Success") { "Green" } else { "Yellow" })
        Write-Host ""
        Write-Host "Output:" -ForegroundColor Cyan
        Write-Host $output.StandardOutputContent
        if ($output.StandardErrorContent) {
            Write-Host "Errors:" -ForegroundColor Red
            Write-Host $output.StandardErrorContent
        }
    } else {
        Write-Host "Failed to send command" -ForegroundColor Red
    }
} else {
    Write-Host "SSM agent is not online (Status: $ssmStatus)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "You need to SSH into the instance to start Ollama:" -ForegroundColor Cyan
    Write-Host "  ssh -i your-key.pem ec2-user@52.0.231.150" -ForegroundColor White
    Write-Host ""
    Write-Host "Then run:" -ForegroundColor Cyan
    Write-Host "  sudo systemctl start ollama" -ForegroundColor White
    Write-Host "  sudo systemctl enable ollama" -ForegroundColor White
    Write-Host "  curl http://localhost:11434/api/tags" -ForegroundColor White
}

