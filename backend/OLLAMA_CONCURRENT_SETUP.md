# Ollama Concurrent Processing Setup

## The Problem

By default, **Ollama processes requests sequentially** - even if you send 30 concurrent HTTP requests, Ollama will queue them and process them one at a time. This means you won't see the performance benefits of concurrent processing.

## The Solution

Configure Ollama to process multiple requests in parallel by setting the `OLLAMA_NUM_PARALLEL` environment variable.

## Setup Instructions

### Windows (PowerShell)

1. **Stop Ollama** if it's running (close the terminal or stop the service)

2. **Set environment variables and start Ollama:**
   ```powershell
   $env:OLLAMA_NUM_PARALLEL = "4"  # Process 4 requests in parallel
   $env:OLLAMA_MAX_LOADED_MODELS = "1"  # Keep model loaded in memory
   ollama serve
   ```

3. **To make it permanent**, create a batch file `start_ollama_concurrent.bat`:
   ```batch
   @echo off
   set OLLAMA_NUM_PARALLEL=4
   set OLLAMA_MAX_LOADED_MODELS=1
   ollama serve
   ```

### Windows (Command Prompt)

```cmd
set OLLAMA_NUM_PARALLEL=4
set OLLAMA_MAX_LOADED_MODELS=1
ollama serve
```

### Linux/Mac

```bash
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=1
ollama serve
```

Or add to your `~/.bashrc` or `~/.zshrc`:
```bash
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=1
```

## Recommended Values

Choose based on your hardware:

| Hardware | OLLAMA_NUM_PARALLEL | Notes |
|----------|---------------------|-------|
| GPU 16GB+ VRAM | 6-8 | Can handle more parallel requests |
| GPU 8-16GB VRAM | 4-6 | Good balance |
| GPU 4-8GB VRAM | 2-4 | Start with 2, increase if stable |
| CPU only (8+ cores) | 2-4 | Depends on CPU cores |
| CPU only (4 cores) | 2 | Limited by CPU |

**Start with 4 and adjust based on:**
- Memory/VRAM usage
- Processing speed
- System stability

## Verification

1. **Check if it's working:**
   - Upload a multi-page PDF (10+ pages)
   - Watch the Ollama terminal/logs
   - You should see multiple requests being processed simultaneously
   - Processing time should be significantly faster

2. **Monitor performance:**
   - With `OLLAMA_NUM_PARALLEL=4`: 10 pages should process in ~2-3x the time of 1 page (not 10x)
   - Without it: 10 pages will take ~10x the time of 1 page

## Performance Impact

- **Without concurrent processing**: 50 pages = 50 × (time per page) = very slow
- **With concurrent processing (4 parallel)**: 50 pages ≈ 12-13 × (time per page) = **~4x faster**

## Troubleshooting

### "Out of Memory" errors
- Reduce `OLLAMA_NUM_PARALLEL` to 2 or 3
- Use a smaller model (e.g., `llama3.2-vision:3b` instead of `llava:13b`)

### Still processing sequentially
- Make sure you set the environment variable **before** starting Ollama
- Restart Ollama after setting the variable
- Check Ollama logs to see if it's processing multiple requests

### Slow performance
- Increase `OLLAMA_NUM_PARALLEL` if you have headroom
- Check GPU/CPU usage - if not maxed out, you can increase parallelism
- Ensure you have enough RAM/VRAM

## Advanced Configuration

### Multiple Models
If you want to keep multiple models loaded:
```bash
export OLLAMA_MAX_LOADED_MODELS=2  # Keep 2 models in memory
```

### Custom Port
```bash
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_NUM_PARALLEL=4
ollama serve
```

## Integration with Your Application

Your application code already sends concurrent requests (up to 30). Once Ollama is configured with `OLLAMA_NUM_PARALLEL`, it will process them in parallel instead of queuing them.

The application will automatically benefit - no code changes needed!

