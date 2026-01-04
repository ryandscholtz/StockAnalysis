# Elastic IP Setup for Ollama EC2 Instance

## Overview

An Elastic IP has been allocated and associated with your Ollama EC2 instance. This ensures the IP address remains constant even when the instance is stopped and started.

## Current Configuration

- **Elastic IP**: `52.0.231.150`
- **Instance ID**: `i-056dc6971b402f0b2`
- **Ollama URL**: `http://52.0.231.150:11434`

## Benefits

1. **Permanent IP Address**: The IP will never change, even after instance stop/start
2. **No More IP Updates**: You won't need to update `.env` file when restarting the instance
3. **Free**: Elastic IPs are free when attached to a running instance
4. **Reliable**: Eliminates connection issues caused by IP changes

## Cost

- **FREE** when attached to a running instance
- **~$0.005/hour** (~$3.60/month) only if the Elastic IP is allocated but not associated with a running instance

## Management

### View Elastic IP Status

```powershell
aws ec2 describe-addresses --profile Cerebrum --region us-east-1 --filters "Name=instance-id,Values=i-056dc6971b402f0b2"
```

### Disassociate Elastic IP (if needed)

```powershell
aws ec2 disassociate-address --association-id <association-id> --profile Cerebrum --region us-east-1
```

### Release Elastic IP (if no longer needed)

```powershell
aws ec2 release-address --allocation-id <allocation-id> --profile Cerebrum --region us-east-1
```

**Warning**: Only release if you're sure you don't need it - you'll lose the IP address permanently!

## Troubleshooting

If Ollama is not accessible:

1. **Check if instance is running**:
   ```powershell
   aws ec2 describe-instances --instance-ids i-056dc6971b402f0b2 --profile Cerebrum --region us-east-1 --query "Reservations[0].Instances[0].State.Name" --output text
   ```

2. **Check if Ollama service is running on EC2**:
   ```bash
   ssh -i your-key.pem ec2-user@52.0.231.150
   sudo systemctl status ollama
   ```

3. **Check security group**:
   - Ensure port 11434 is open for inbound traffic
   - Source: `0.0.0.0/0` (or your specific IP)

4. **Test connectivity**:
   ```powershell
   curl http://52.0.231.150:11434/api/tags
   ```

## Next Steps

1. ✅ Elastic IP allocated and associated
2. ✅ `.env` file updated with Elastic IP
3. ⏳ Restart backend server (already done)
4. ⏳ Test PDF upload

The IP address will now remain constant, eliminating the need for manual updates!

