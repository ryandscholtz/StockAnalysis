# Llama/Ollama Setup for PDF Extraction

This guide explains how to set up Llama (local or hosted) for PDF image extraction and analysis.

## Option 1: Local Ollama (Recommended for Development)

### Installation

1. **Install Ollama**:
   - Windows: Download from https://ollama.com/download
   - Or use: `winget install Ollama.Ollama`
   - Or: `curl -fsSL https://ollama.com/install.sh | sh` (Linux/Mac)

2. **Pull a vision-capable model**:
   ```bash
   ollama pull llama3.2-vision:11b
   # Or for smaller/faster: llama3.2-vision:3b
   # Or for better quality: llava:13b
   ```

3. **Start Ollama** (usually runs automatically):
   ```bash
   ollama serve
   ```
   This starts the API server at `http://localhost:11434`

4. **Configure Ollama for Concurrent Processing** (IMPORTANT for performance):
   
   By default, Ollama processes requests sequentially. To enable concurrent processing (which significantly speeds up PDF processing), set these environment variables before starting Ollama:
   
   **Windows (PowerShell):**
   ```powershell
   $env:OLLAMA_NUM_PARALLEL = "4"  # Number of parallel requests (adjust based on your GPU/CPU)
   $env:OLLAMA_MAX_LOADED_MODELS = "1"  # Keep model loaded in memory
   ollama serve
   ```
   
   **Windows (Command Prompt):**
   ```cmd
   set OLLAMA_NUM_PARALLEL=4
   set OLLAMA_MAX_LOADED_MODELS=1
   ollama serve
   ```
   
   **Linux/Mac:**
   ```bash
   export OLLAMA_NUM_PARALLEL=4
   export OLLAMA_MAX_LOADED_MODELS=1
   ollama serve
   ```
   
   **Recommended values:**
   - **GPU with 8GB+ VRAM**: `OLLAMA_NUM_PARALLEL=4` to `8`
   - **GPU with 4-8GB VRAM**: `OLLAMA_NUM_PARALLEL=2` to `4`
   - **CPU only**: `OLLAMA_NUM_PARALLEL=2` to `4` (depends on CPU cores)
   
   **Note**: Higher values use more memory/VRAM. Start with 4 and adjust based on your system.

### Configuration

Add to your `.env` file:
```bash
LLM_PROVIDER=llama
LLAMA_API_URL=http://localhost:11434
LLAMA_MODEL=llama3.2-vision:11b
```

## Option 2: Hosted Llama Instance

If you have a hosted Llama instance (e.g., on a server, cloud, or using OpenAI-compatible API):

### Configuration

Add to your `.env` file:
```bash
LLM_PROVIDER=llama
LLAMA_API_URL=https://your-hosted-instance.com/v1
LLAMA_MODEL=your-model-name
LLAMA_API_KEY=your-api-key  # Optional, if your instance requires authentication
```

### Supported Hosted Services

- **Ollama Cloud**: Use your Ollama Cloud URL
- **OpenAI-compatible APIs**: Any service that supports OpenAI's chat completions format
- **Custom deployments**: Any Llama instance with OpenAI-compatible API

## Available Vision Models

Recommended models for PDF extraction:

1. **llama3.2-vision:11b** - Good balance of quality and speed
2. **llama3.2-vision:3b** - Faster, smaller, good for testing
3. **llava:13b** - Excellent vision capabilities
4. **llava:7b** - Faster alternative to llava:13b

## Testing

1. Make sure Ollama is running:
   ```bash
   ollama list  # Should show your installed models
   ```

2. Test the API:
   ```bash
   curl http://localhost:11434/api/tags  # Should return available models
   ```

3. Upload a PDF in the application - it will use Llama for extraction

## Performance Notes

- **Local models** run on your machine - no API costs, but requires GPU/CPU resources
- **11B models** typically need 16GB+ RAM or GPU with 8GB+ VRAM
- **3B models** can run on 8GB RAM
- Processing time depends on your hardware (GPU is much faster)

## Troubleshooting

### Model not found
```bash
ollama pull llama3.2-vision:11b
```

### Ollama not running
```bash
ollama serve
```

### Connection refused
- Check that Ollama is running on port 11434
- Verify `LLAMA_API_URL` in `.env` matches your Ollama instance

### Out of memory
- Use a smaller model: `llama3.2-vision:3b`
- Or reduce concurrent requests in the code
- Reduce `OLLAMA_NUM_PARALLEL` if set too high

### Slow processing / Sequential processing
- **Check if Ollama is configured for concurrent processing**: By default, Ollama processes requests one at a time
- Set `OLLAMA_NUM_PARALLEL=4` (or higher) before starting Ollama
- Verify by checking Ollama logs - you should see multiple requests being processed simultaneously
- If requests are still sequential, restart Ollama with the environment variable set

## Switching Between Providers

### Quick Switch (Automated)

Use the provided script to switch providers:

**Windows (PowerShell):**
```powershell
.\switch_llm_provider.ps1 llama
.\switch_llm_provider.ps1 anthropic
.\switch_llm_provider.ps1 openai
```

**Linux/Mac (Bash):**
```bash
chmod +x switch_llm_provider.sh
./switch_llm_provider.sh llama
./switch_llm_provider.sh anthropic
./switch_llm_provider.sh openai
```

### Manual Switch

You can also manually change `LLM_PROVIDER` in `.env`:

```bash
# Use Llama (local)
LLM_PROVIDER=llama
LLAMA_API_URL=http://localhost:11434
LLAMA_MODEL=llava:7b

# Use Anthropic Claude
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key

# Use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
```

**Remember to restart your backend server after changing providers!**

