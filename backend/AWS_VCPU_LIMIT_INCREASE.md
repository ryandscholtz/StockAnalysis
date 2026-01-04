# AWS vCPU Limit Increase Guide

## Current Situation

Your Cerebrum AWS account has vCPU limits that prevent launching GPU instances (g4dn.xlarge). The current limit appears to be 0 for GPU instances.

## How to Request vCPU Limit Increases

### Option 1: AWS Support Console (Recommended)

1. **Go to AWS Support Center:**
   - Log into AWS Console: https://console.aws.amazon.com/
   - Navigate to: **Support** → **Support Center** → **Create Case**

2. **Create a Service Limit Increase Request:**
   - **Limit Type**: EC2 Instances
   - **Region**: us-east-1 (or your preferred region)
   - **Primary Instance Type**: g4dn.xlarge (or g4dn.2xlarge for more power)
   - **New Limit Value**: 8 (or more if needed)
   - **Use Case**: "Running Ollama for PDF processing with vision models. Need GPU instances for faster inference."

3. **Submit the Request:**
   - Usually approved within 24-48 hours
   - Sometimes approved within hours for reasonable requests

### Option 2: AWS CLI Command

```bash
aws service-quotas request-service-quota-increase \
    --profile Cerebrum \
    --service-code ec2 \
    --quota-code L-DB2E81BA \
    --desired-value 8 \
    --region us-east-1
```

**Note**: The quota code varies by instance type. For g4dn.xlarge, you may need to find the specific quota code.

### Option 3: Check Current Limits

```bash
# Check current EC2 limits
aws service-quotas list-service-quotas \
    --profile Cerebrum \
    --service-code ec2 \
    --region us-east-1 \
    --query "Quotas[?contains(QuotaName, 'Running On-Demand')]"
```

## Instance Type Limits

Different instance families have separate limits:

- **General Purpose (t3, m5, etc.)**: Usually higher limits
- **GPU Instances (g4dn, p3, etc.)**: Usually lower limits, require request
- **Compute Optimized (c5, etc.)**: Moderate limits

## Quick Reference

### Current Instance (t3.xlarge)
- **vCPUs**: 4
- **RAM**: 16GB
- **Concurrent**: 4-8 requests
- **Cost**: ~$0.17/hour
- **Status**: ✅ Working, no limit increase needed

### GPU Instance (g4dn.xlarge) - Requires Limit Increase
- **vCPUs**: 4
- **GPU**: NVIDIA T4 (16GB VRAM)
- **RAM**: 16GB
- **Concurrent**: 8+ requests
- **Cost**: ~$0.75/hour
- **Status**: ⚠️ Requires vCPU limit increase

## After Limit Increase

Once approved, you can:

1. **Stop current instance:**
   ```bash
   aws ec2 stop-instances --instance-ids i-xxxxx --profile Cerebrum
   ```

2. **Modify to GPU instance:**
   ```bash
   aws ec2 modify-instance-attribute \
       --instance-id i-xxxxx \
       --instance-type Value=g4dn.xlarge \
       --profile Cerebrum
   ```

3. **Start instance:**
   ```bash
   aws ec2 start-instances --instance-ids i-xxxxx --profile Cerebrum
   ```

## Alternative: Use Different Region

Some regions may have different default limits. Try:

```bash
# Check limits in different regions
aws service-quotas list-service-quotas \
    --profile Cerebrum \
    --service-code ec2 \
    --region us-west-2 \
    --query "Quotas[?contains(QuotaName, 'g4dn')]"
```

## Cost Comparison

| Instance | vCPUs | GPU | Cost/Hour | Concurrent | 50 Pages Time |
|----------|-------|-----|-----------|------------|----------------|
| t3.medium | 2 | No | $0.04 | 2-4 | ~15-25 min |
| t3.xlarge | 4 | No | $0.17 | 4-8 | ~6-12 min |
| g4dn.xlarge | 4 | Yes | $0.75 | 8+ | ~2-4 min |

## Recommendation

1. **For now**: Use t3.xlarge (already upgraded) - good balance of cost and performance
2. **For production**: Request GPU limit increase and use g4dn.xlarge for best performance
3. **For cost optimization**: Use t3.xlarge and stop instance when not in use

