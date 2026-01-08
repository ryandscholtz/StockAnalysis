# How to Start Ollama on EC2 Instance

## Current Status

- **EC2 Instance**: Running (`i-056dc6971b402f0b2`)
- **Elastic IP**: `52.0.231.150` (permanent)
- **Port 11434**: Open in security group
- **Ollama Service**: Not running (needs to be started)

## Quick Start

### Option 1: SSH into EC2 (Recommended)

1. **SSH into the instance**:
   ```bash
   ssh -i your-key.pem ec2-user@52.0.231.150
   ```
   *(Replace `your-key.pem` with your actual key file path)*

2. **Check Ollama status**:
   ```bash
   sudo systemctl status ollama
   ```

3. **Start Ollama**:
   ```bash
   sudo systemctl start ollama
   ```

4. **Enable Ollama to start on boot**:
   ```bash
   sudo systemctl enable ollama
   ```

5. **Verify Ollama is running**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

6. **Check if model is available**:
   ```bash
   ollama list
   ```

7. **If model is missing, pull it**:
   ```bash
   ollama pull llama3.2-vision:11b
   ```

### Option 2: Use AWS Systems Manager (if configured)

If SSM agent is installed and configured:

```powershell
.\start_ollama_ssm.ps1 -Profile Cerebrum
```

## Troubleshooting

### Ollama service won't start

1. **Check logs**:
   ```bash
   sudo journalctl -u ollama -n 50
   ```

2. **Check if Ollama is installed**:
   ```bash
   which ollama
   ollama --version
   ```

3. **Reinstall Ollama if needed**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

### Port 11434 not accessible

1. **Check if Ollama is listening**:
   ```bash
   sudo netstat -tlnp | grep 11434
   ```

2. **Check firewall**:
   ```bash
   sudo firewall-cmd --list-ports
   sudo firewall-cmd --add-port=11434/tcp --permanent
   sudo firewall-cmd --reload
   ```

### Model not found

If `llama3.2-vision:11b` is not available:

```bash
ollama pull llama3.2-vision:11b
```

## Verify Everything Works

After starting Ollama, test from your local machine:

```powershell
curl http://52.0.231.150:11434/api/tags
```

You should see a JSON response with available models.

## Auto-Start on Boot

To ensure Ollama starts automatically when the instance reboots:

```bash
sudo systemctl enable ollama
sudo systemctl status ollama
```

## Next Steps

Once Ollama is running:

1. ✅ Test connectivity: `curl http://52.0.231.150:11434/api/tags`
2. ✅ Try uploading a PDF again
3. ✅ The system should now extract financial data successfully

