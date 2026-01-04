# Ollama on AWS EC2 - Direct Connection Setup

This guide sets up Ollama on AWS EC2 with direct connection capability, so your backend can connect directly to Ollama without uploading files through your local machine.

## Quick Start

### 1. Run the Deployment Script

```powershell
cd C:\Users\Admin\Documents\GitHub\StockAnalysis\backend
.\deploy_ollama_ec2.ps1 -Profile Cerebrum
```

This will:
- ✅ Create an EC2 instance (g4dn.xlarge with GPU)
- ✅ Install Ollama automatically
- ✅ Download llama3.2-vision:11b model
- ✅ Configure for 8 concurrent requests
- ✅ Set up security groups
- ✅ Provide you with the connection URL

### 2. Update Your Backend Configuration

After deployment, update your `.env` file:

```bash
LLAMA_API_URL=http://YOUR_EC2_PUBLIC_IP:11434
LLAMA_MODEL=llama3.2-vision:11b
```

The deployment script will show you the exact IP address to use.

## Architecture

```
┌─────────────────┐
│  Your Backend   │
│  (FastAPI)      │
│  on your PC     │
└────────┬────────┘
         │
         │ Direct HTTP Connection
         │ (port 11434)
         │
┌────────▼────────┐
│  AWS EC2        │
│  g4dn.xlarge    │
│  Ollama Server  │
│  OLLAMA_NUM_    │
│  PARALLEL=8     │
└─────────────────┘
```

**Benefits:**
- ✅ Direct connection - no file uploads through your PC
- ✅ Faster processing - GPU acceleration
- ✅ Concurrent processing - 8 pages at once
- ✅ Always available - runs 24/7 (or stop when not needed)

## Instance Types

### Recommended: GPU Instance (g4dn.xlarge)
- **Cost**: ~$0.75/hour (~$18/day if running 24/7)
- **GPU**: NVIDIA T4 (16GB VRAM)
- **CPU**: 4 vCPUs
- **RAM**: 16GB
- **Best for**: Production, high volume

### Alternative: CPU Instance (c5.2xlarge)
- **Cost**: ~$0.34/hour (~$8/day if running 24/7)
- **CPU**: 8 vCPUs
- **RAM**: 16GB
- **Best for**: Development, lower volume, cost-sensitive

To use CPU instance:
```powershell
.\deploy_ollama_ec2.ps1 -Profile Cerebrum -InstanceType c5.2xlarge
```

## Cost Management

### Option 1: Stop When Not in Use (Recommended)

Stop the instance when not processing PDFs:
```bash
aws ec2 stop-instances --instance-ids i-xxxxx --profile Cerebrum
```

Start when needed:
```bash
aws ec2 start-instances --instance-ids i-xxxxx --profile Cerebrum
```

**Note**: When you stop/start, the public IP may change. Check the IP after restarting.

### Option 2: Use Spot Instances (60-90% cheaper)

Modify the script to use spot instances for even lower costs.

### Option 3: Scheduled Start/Stop

Use AWS EventBridge to automatically start/stop the instance on a schedule.

## Security

### Current Setup
- ✅ SSH (port 22) restricted to your IP
- ⚠️ Ollama API (port 11434) open to internet

### Recommended: Restrict Ollama Port

For better security, restrict port 11434 to your backend's IP:

```bash
# Get your backend's public IP
$backendIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content

# Update security group
aws ec2 authorize-security-group-ingress \
    --profile Cerebrum \
    --region us-east-1 \
    --group-id sg-xxxxx \
    --protocol tcp \
    --port 11434 \
    --cidr "$backendIp/32"
```

Or use a VPN/private network for even better security.

## Monitoring

### Check Ollama Status

```bash
# From your PC
curl http://YOUR_EC2_IP:11434/api/tags

# Should return list of available models
```

### SSH into Instance

```bash
ssh -i ollama-keypair.pem ubuntu@YOUR_EC2_IP
```

### View Ollama Logs

```bash
sudo journalctl -u ollama -f
```

### Check System Resources

```bash
# CPU and memory
htop

# GPU usage (if GPU instance)
nvidia-smi
```

## Troubleshooting

### Ollama Not Responding

1. **Check if instance is running:**
   ```bash
   aws ec2 describe-instances --instance-ids i-xxxxx --profile Cerebrum
   ```

2. **SSH into instance and check Ollama:**
   ```bash
   ssh -i ollama-keypair.pem ubuntu@YOUR_EC2_IP
   sudo systemctl status ollama
   sudo journalctl -u ollama -n 50
   ```

3. **Restart Ollama service:**
   ```bash
   sudo systemctl restart ollama
   ```

### Model Not Downloaded

The user data script should download the model automatically. If it didn't:

```bash
ssh -i ollama-keypair.pem ubuntu@YOUR_EC2_IP
export OLLAMA_NUM_PARALLEL=8
ollama pull llama3.2-vision:11b
```

### Connection Refused

1. **Check security group** - ensure port 11434 is open
2. **Check instance status** - ensure it's running
3. **Check Ollama service** - SSH in and check `sudo systemctl status ollama`

### High Costs

- **Stop instance when not in use** (saves 100% when stopped)
- **Use smaller instance type** (c5.2xlarge instead of g4dn.xlarge)
- **Use spot instances** (60-90% cheaper, but can be interrupted)

## Updating Configuration

### Change Concurrent Requests

SSH into instance and edit the service:

```bash
ssh -i ollama-keypair.pem ubuntu@YOUR_EC2_IP
sudo nano /etc/systemd/system/ollama.service
# Change OLLAMA_NUM_PARALLEL=8 to desired value
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Change Model

```bash
ssh -i ollama-keypair.pem ubuntu@YOUR_EC2_IP
ollama pull llava:13b  # or other model
# Update your .env: LLAMA_MODEL=llava:13b
```

## Cleanup

To remove everything:

```bash
# Stop and terminate instance
aws ec2 terminate-instances --instance-ids i-xxxxx --profile Cerebrum

# Delete key pair (optional)
aws ec2 delete-key-pair --key-name ollama-keypair --profile Cerebrum

# Delete security group (optional)
aws ec2 delete-security-group --group-id sg-xxxxx --profile Cerebrum
```

## Next Steps

1. ✅ Run deployment script
2. ✅ Update `.env` with EC2 IP
3. ✅ Test connection
4. ✅ Process a PDF to verify everything works
5. ✅ Set up cost monitoring/alerts in AWS

## Support

If you encounter issues:
1. Check the deployment script output
2. SSH into instance and check logs
3. Verify security group rules
4. Check AWS CloudWatch logs

