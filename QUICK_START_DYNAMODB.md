# Quick Start: Deploy DynamoDB

## 🚀 Quick Deployment (5 minutes)

### Step 1: Install CDK (if not already installed)
```bash
npm install -g aws-cdk
```

### Step 2: Deploy Infrastructure
```bash
cd infrastructure

# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap --profile Cerebrum  # or Personal

# Deploy
cdk deploy --profile Cerebrum
```

**Or use the PowerShell script:**
```powershell
cd infrastructure
.\deploy.ps1
```

### Step 3: Configure Backend

Create `backend/.env`:
```bash
USE_DYNAMODB=true
DYNAMODB_TABLE_NAME=stock-analyses
DYNAMODB_REGION=us-east-1
AWS_PROFILE=Cerebrum  # or Personal
```

### Step 4: Test It!

```bash
cd backend
python batch_analyze_exchange.py JSE jse_tickers.txt
```

You should see: `Using DynamoDB: stock-analyses in us-east-1`

## ✅ That's It!

Your batch analysis now uses DynamoDB automatically.

## 📋 What Was Created

- **DynamoDB Table**: `stock-analyses`
- **3 Global Secondary Indexes** for efficient querying
- **Auto-scaling**: Pay-per-request pricing
- **Backup**: Point-in-time recovery enabled

## 🔍 Verify Deployment

```bash
aws dynamodb describe-table --table-name stock-analyses --profile Cerebrum
```

## 💰 Cost

- **Free Tier**: 25GB storage, 25 RCU/WCU (always free)
- **After Free Tier**: ~$1-5/month for typical usage

## 📚 Full Documentation

See `DYNAMODB_SETUP.md` for detailed instructions.

