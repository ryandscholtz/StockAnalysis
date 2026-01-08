# EC2 Auto-Start Guide

## Overview

The EC2 auto-start feature automatically starts your Ollama EC2 instance when PDF processing is needed, then you can stop it manually to save costs. This gives you **pay-per-use** pricing instead of running 24/7.

## How It Works

```
┌─────────────────┐
│  User uploads   │
│  PDF file        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Backend checks │
│  EC2 status     │
└────────┬────────┘
         │
    ┌────┴────┐
    │        │
    ▼        ▼
┌──────┐  ┌──────────┐
│Running│  │ Stopped   │
└───┬──┘  └─────┬──────┘
    │           │
    │           │ Auto-start
    │           ▼
    │      ┌──────────┐
    │      │ Starting │
    │      │ (2 min)  │
    │      └─────┬────┘
    │            │
    └────────────┘
         │
         ▼
┌─────────────────┐
│  Process PDF    │
│  with Ollama    │
└─────────────────┘
```

## Setup

### 1. Install Dependencies

The auto-start feature requires `boto3`:

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install boto3
```

### 2. Run Setup Script

```powershell
.\setup_ec2_auto_start.ps1
```

This will:
- ✅ Install boto3 if needed
- ✅ Update `.env` with EC2 settings
- ✅ Configure auto-start parameters

### 3. Configure .env

The setup script adds these to your `.env`:

```bash
# Enable EC2 auto-start
EC2_AUTO_START=true

# EC2 instance details
OLLAMA_EC2_INSTANCE_ID=i-056dc6971b402f0b2
AWS_PROFILE=Cerebrum
AWS_REGION=us-east-1

# Optional: Customize timing
EC2_STARTUP_WAIT_SECONDS=120  # Max wait for instance to start
EC2_AUTO_SHUTDOWN_MINUTES=15  # Future: auto-shutdown after idle
```

### 4. Restart Backend

Restart your backend server to pick up the new configuration:

```powershell
# Stop current server (Ctrl+C)
# Then restart
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Usage

### Automatic Start

1. **Upload a PDF** through the frontend
2. **Backend automatically:**
   - Checks if EC2 instance is running
   - If stopped, starts it automatically
   - Waits ~2 minutes for instance to be ready
   - Processes the PDF
3. **Done!** Instance stays running (you can stop it manually)

### Manual Stop (Save Money!)

After processing, stop the instance to save costs:

```powershell
.\manage_ollama_instance.ps1 stop
```

**Cost when stopped:** ~$0.10/month (just storage)

**Cost when running:** ~$0.17/hour (~$121/month if 24/7 for t3.xlarge)

## Cost Comparison

| Scenario | Monthly Cost | Notes |
|----------|--------------|-------|
| **Auto-start + Manual stop** | **~$5-15** | Only pay when processing |
| Always running (t3.xlarge) | ~$121 | 24/7 availability |
| Always running (t3.medium) | ~$30 | 24/7 availability |

**Example:** If you process PDFs 2-4 hours/week:
- Auto-start: ~$5-10/month
- Always on: ~$121/month (xlarge) or ~$30/month (medium)

**Savings:** $91-116/month with auto-start!

## How It Works (Technical)

1. **PDFExtractor** checks `EC2_AUTO_START` environment variable
2. If enabled and using EC2 Ollama (not localhost), it calls `EC2Manager.ensure_running()`
3. **EC2Manager** uses boto3 to:
   - Check instance state via AWS API
   - Start instance if stopped
   - Wait for instance to be running
   - Get current public IP
   - Update `LLAMA_API_URL` if IP changed
4. Processing continues normally

## Troubleshooting

### Instance Won't Start

**Error:** "EC2 client not available"

**Solution:** 
- Check AWS credentials: `aws configure list --profile Cerebrum`
- Verify instance ID in `.env` is correct
- Check IAM permissions (need `ec2:StartInstances`, `ec2:DescribeInstances`)

### Slow Startup

**Issue:** Takes 2+ minutes to start

**Solution:**
- This is normal! EC2 instances take 1-2 minutes to boot
- Ollama needs additional time to start (~10 seconds)
- Consider leaving instance running if you process frequently

### IP Changed After Start

**Issue:** Connection fails after restart

**Solution:**
- Auto-start feature updates `LLAMA_API_URL` automatically
- If issues persist, check `.env` has correct IP
- Restart backend after instance starts

### boto3 Not Found

**Error:** "No module named 'boto3'"

**Solution:**
```powershell
.\venv\Scripts\python.exe -m pip install boto3
```

## Advanced: SQS-Based Auto-Start (Future)

For more advanced use cases, you could use:

1. **SQS Queue** - Queue processing requests
2. **Lambda Function** - Triggered by SQS, starts EC2
3. **EC2 User Data** - Polls SQS for work, shuts down when idle

This would provide:
- ✅ True queue-based processing
- ✅ Automatic idle shutdown
- ✅ Better scalability

Let me know if you'd like this implemented!

## Disable Auto-Start

To disable auto-start and manage instance manually:

```bash
# In .env
EC2_AUTO_START=false
```

Then restart backend.

## Summary

✅ **Auto-start enabled** = Instance starts automatically when needed  
✅ **Manual stop** = Save money when not processing  
✅ **Pay-per-use** = Only pay for actual processing time  
✅ **Simple setup** = One script configures everything  

**Best practice:** Enable auto-start, process PDFs, then stop instance manually to save costs!

