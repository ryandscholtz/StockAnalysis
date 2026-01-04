# EC2 Cost Optimization Guide

## t3.xlarge Cost Breakdown

### Pricing (us-east-1)
- **On-Demand**: $0.1664/hour
- **Per Day** (24 hours): ~$4.00
- **Per Month** (730 hours): ~$121.47

### Real-World Usage Scenarios

| Usage Pattern | Monthly Cost | Annual Cost |
|---------------|--------------|-------------|
| **24/7 Always On** | ~$121 | ~$1,452 |
| **8 hours/day (business hours)** | ~$40 | ~$480 |
| **4 hours/day** | ~$20 | ~$240 |
| **2 hours/day** | ~$10 | ~$120 |
| **Pay-per-use (stop when done)** | ~$5-15 | ~$60-180 |

## Cost Optimization Strategies

### 1. Stop Instance When Not in Use (BEST SAVINGS)

**Savings**: 100% when stopped (only pay for EBS storage: ~$0.10/month for 20GB)

```powershell
# Stop instance
aws ec2 stop-instances --instance-ids i-056dc6971b402f0b2 --profile Cerebrum

# Start when needed
aws ec2 start-instances --instance-ids i-056dc6971b402f0b2 --profile Cerebrum
```

**Example**: If you process PDFs 2 hours/day:
- Running 24/7: $121/month
- Stop when done: ~$10/month
- **Savings: $111/month (92% reduction!)**

### 2. Use Smaller Instance for Development

For testing/development, use `t3.medium`:
- **Cost**: $0.0416/hour (4x cheaper)
- **Performance**: Still handles 2-4 concurrent requests
- **Monthly (2h/day)**: ~$2.50

### 3. Scheduled Start/Stop

Use AWS EventBridge to automatically start/stop:

**Start at 9 AM, Stop at 5 PM (8 hours/day)**:
- Cost: ~$40/month
- Always ready during business hours
- Automatic, no manual intervention

### 4. Spot Instances (Advanced)

Use Spot instances for 60-90% discount:
- **Risk**: Can be interrupted (not ideal for long-running services)
- **Best for**: Batch processing, non-critical workloads
- **Savings**: $0.05-0.07/hour instead of $0.17/hour

### 5. Reserved Instances (Long-term)

If running 24/7 for 1-3 years:
- **1-year Reserved**: ~$0.10/hour (40% discount)
- **3-year Reserved**: ~$0.07/hour (58% discount)
- **Monthly**: ~$73 (1-year) or ~$51 (3-year)

## Cost Comparison

| Instance Type | Hourly | 2h/day | 8h/day | 24/7 |
|---------------|--------|--------|--------|------|
| **t3.medium** | $0.0416 | $2.50 | $10 | $30 |
| **t3.xlarge** | $0.1664 | $10 | $40 | $121 |
| **g4dn.xlarge** (GPU) | $0.752 | $45 | $180 | $549 |

## Recommended Setup

### For Personal/Development Use:
```
1. Use t3.xlarge
2. Stop instance when not processing PDFs
3. Start only when needed
4. Expected cost: $5-15/month
```

### For Production/Regular Use:
```
1. Use t3.xlarge
2. Schedule: Start 8 AM, Stop 6 PM (weekdays)
3. Manual start for weekend processing
4. Expected cost: $40-50/month
```

### For High Volume:
```
1. Request GPU limit increase
2. Use g4dn.xlarge
3. Process in batches
4. Stop when not in use
5. Expected cost: $50-100/month (depending on usage)
```

## Quick Cost Calculator

**Formula**: `Hours per month × $0.1664 = Monthly cost`

Examples:
- 10 hours/month = $1.66
- 30 hours/month = $5.00
- 60 hours/month = $10.00
- 240 hours/month (8h/day) = $40.00

## Stop/Start Script

Create `manage_ollama_instance.ps1`:

```powershell
param([string]$Action = "status", [string]$Profile = "Cerebrum")
$InstanceId = "i-056dc6971b402f0b2"

if ($Action -eq "stop") {
    aws ec2 stop-instances --instance-ids $InstanceId --profile $Profile
    Write-Host "Stopping instance..." -ForegroundColor Yellow
} elseif ($Action -eq "start") {
    aws ec2 start-instances --instance-ids $InstanceId --profile $Profile
    Write-Host "Starting instance..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    $ip = aws ec2 describe-instances --profile $Profile --region us-east-1 --instance-ids $InstanceId --query "Reservations[0].Instances[0].PublicIpAddress" --output text
    Write-Host "Instance IP: $ip" -ForegroundColor Green
} else {
    $state = aws ec2 describe-instances --profile $Profile --region us-east-1 --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text
    Write-Host "Instance status: $state" -ForegroundColor Cyan
}
```

Usage:
```powershell
.\manage_ollama_instance.ps1 stop    # Stop to save money
.\manage_ollama_instance.ps1 start   # Start when needed
.\manage_ollama_instance.ps1 status  # Check status
```

## Bottom Line

**t3.xlarge is NOT very expensive IF you:**
- ✅ Stop it when not in use: **$5-15/month** (very affordable)
- ✅ Use it 2-4 hours/day: **$10-20/month** (reasonable)
- ✅ Run 24/7: **$121/month** (only if you need it always on)

**Recommendation**: Stop the instance when you're done processing PDFs. You'll save 90%+ on costs while still having it available when needed.

