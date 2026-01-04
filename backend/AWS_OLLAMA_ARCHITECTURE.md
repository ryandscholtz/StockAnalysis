# AWS Ollama Deployment Architecture Analysis

## Question: Spawn One Instance Per Page?

**Short Answer: No, this is NOT recommended.** Here's why and what to do instead.

## Problems with One Instance Per Page

### 1. **Model Loading Overhead** ⚠️
- **Cold Start Time**: Each new instance must load the model into memory/VRAM
- **Time Cost**: Model loading takes 10-30 seconds for a 7B-13B model
- **Impact**: For a 50-page PDF, you'd wait 10-30 seconds × 50 = 8-25 minutes just for startup
- **Current Approach**: One instance with model already loaded = 0 seconds startup

### 2. **Resource Waste** 💰
- **Memory Duplication**: Each instance needs full model in memory (7B model = ~14GB RAM, 13B = ~26GB)
- **Cost**: AWS GPU instances (g4dn.xlarge) cost ~$0.50-1.00/hour
- **Example**: 50 pages = 50 instances × $0.75/hour = $37.50/hour (even if only used for 1 minute)
- **Current Approach**: One instance handles all pages = $0.75/hour

### 3. **Network Latency** 🌐
- **API Calls**: Each page requires HTTP request to different instance
- **Latency**: 50-200ms per request (even within AWS)
- **Current Approach**: All requests to same instance = minimal latency

### 4. **Complexity** 🔧
- **Orchestration**: Need to manage instance lifecycle, health checks, cleanup
- **Load Balancing**: Need to distribute requests across instances
- **Error Handling**: What if an instance fails mid-processing?
- **Current Approach**: Simple - one instance, one API endpoint

## Better Alternatives

### Option 1: Single Instance with OLLAMA_NUM_PARALLEL (Recommended) ⭐

**Best for: Most use cases**

```bash
# On AWS EC2 instance (g4dn.xlarge or larger)
export OLLAMA_NUM_PARALLEL=8  # Process 8 pages simultaneously
ollama serve
```

**Benefits:**
- ✅ Model loaded once (fast startup)
- ✅ Handles 4-8 concurrent requests efficiently
- ✅ Low cost (~$0.75/hour for g4dn.xlarge)
- ✅ Simple architecture
- ✅ 50 pages in ~6-12 batches = 2-4 minutes total

**Cost**: ~$0.75/hour = $18/day if running 24/7, or pay-per-use

### Option 2: AWS ECS/Fargate with Multiple Containers (For High Volume)

**Best for: High traffic, multiple users**

```
ECS Service:
  - Task Definition: Ollama container
  - Desired Count: 2-4 tasks (each with OLLAMA_NUM_PARALLEL=4)
  - Auto-scaling: Scale based on CPU/GPU utilization
  - Load Balancer: Distribute requests across tasks
```

**Benefits:**
- ✅ Auto-scaling based on demand
- ✅ Fault tolerance (if one container fails, others continue)
- ✅ Can handle multiple users simultaneously
- ✅ Pay only for what you use (Fargate)

**Cost**: ~$0.75/hour × number of running tasks

### Option 3: AWS SageMaker Multi-Model Endpoint

**Best for: Enterprise, multiple models**

- Deploy Ollama as a SageMaker endpoint
- Supports multiple models
- Auto-scaling built-in
- More expensive but enterprise-grade

**Cost**: ~$1-2/hour + data transfer

### Option 4: AWS Lambda + ECS (Hybrid)

**Best for: Sporadic usage**

- Use Lambda to trigger ECS tasks
- ECS tasks process batches of pages
- Shut down when not in use
- Good for occasional processing

**Cost**: Pay only when processing

## Performance Comparison

### Scenario: 50-page PDF processing

| Approach | Startup Time | Processing Time | Total Time | Cost |
|----------|-------------|----------------|------------|------|
| **One instance per page** | 10-30s × 50 = 8-25 min | 5-10s × 50 = 4-8 min | **12-33 minutes** | **$37.50** |
| **Single instance (OLLAMA_NUM_PARALLEL=8)** | 0s | 5-10s × 7 batches = 35-70s | **35-70 seconds** | **$0.01** |
| **ECS with 4 containers** | 0s (already running) | 5-10s × 2 batches = 10-20s | **10-20 seconds** | **$0.02** |

**Winner**: Single instance with OLLAMA_NUM_PARALLEL (or ECS for high volume)

## Recommended Architecture

### For Development / Low Volume

```
┌─────────────────┐
│  Your Backend   │
│  (FastAPI)      │
└────────┬────────┘
         │
         │ HTTP Requests (30 concurrent)
         │
┌────────▼────────┐
│  AWS EC2        │
│  g4dn.xlarge    │
│  Ollama         │
│  OLLAMA_NUM_    │
│  PARALLEL=8     │
└─────────────────┘
```

**Cost**: ~$0.75/hour = $18/day (or stop when not in use)

### For Production / High Volume

```
┌─────────────────┐
│  Your Backend   │
│  (FastAPI)      │
└────────┬────────┘
         │
         │ HTTP Requests
         │
┌────────▼────────┐
│  Application    │
│  Load Balancer │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼───┐
│ ECS   │ │ ECS  │
│ Task 1│ │ Task2│
│ Ollama│ │Ollama│
│ (8x)  │ │ (8x) │
└───────┘ └──────┘
```

**Cost**: ~$0.75/hour × number of tasks (auto-scales)

## Implementation Guide

### Option 1: Single EC2 Instance (Recommended Start)

1. **Launch EC2 Instance:**
   ```bash
   # Instance type: g4dn.xlarge (GPU) or c5.2xlarge (CPU)
   # AMI: Ubuntu 22.04 LTS
   # Storage: 50GB
   ```

2. **Install Ollama:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3.2-vision:11b
   ```

3. **Configure for Concurrent Processing:**
   ```bash
   export OLLAMA_NUM_PARALLEL=8
   export OLLAMA_MAX_LOADED_MODELS=1
   ollama serve --host 0.0.0.0
   ```

4. **Update Your Backend:**
   ```bash
   # In .env
   LLAMA_API_URL=http://your-ec2-ip:11434
   ```

5. **Security Group:**
   - Allow inbound port 11434 from your backend's IP
   - Or use VPN/private network

### Option 2: ECS with Fargate (For Production)

1. **Create Docker Image:**
   ```dockerfile
   FROM ollama/ollama:latest
   ENV OLLAMA_NUM_PARALLEL=8
   CMD ["ollama", "serve", "--host", "0.0.0.0"]
   ```

2. **Deploy to ECS:**
   - Create ECS cluster
   - Create task definition with GPU support
   - Create service with desired count = 2-4
   - Add Application Load Balancer

3. **Update Backend:**
   ```bash
   LLAMA_API_URL=http://your-alb-dns-name:11434
   ```

## Cost Optimization Tips

1. **Use Spot Instances**: 60-90% cheaper (good for non-critical workloads)
2. **Auto-Stop**: Stop EC2 when not in use (saves 90%+ cost)
3. **Reserved Instances**: 30-50% discount for 1-3 year commitment
4. **Right-Size**: Start with g4dn.xlarge, scale up if needed

## Monitoring

Track these metrics:
- **Request latency**: Should be < 10s per page
- **Concurrent requests**: Should match OLLAMA_NUM_PARALLEL
- **GPU utilization**: Should be 70-90% during processing
- **Cost**: Monitor CloudWatch billing

## Conclusion

**Don't spawn one instance per page.** Instead:

1. **Start with**: Single EC2 instance + OLLAMA_NUM_PARALLEL=8
2. **Scale to**: ECS with 2-4 containers if you need more throughput
3. **Avoid**: One instance per page (too slow, too expensive, too complex)

The single instance approach with concurrent processing is:
- **10-20x faster** (no startup overhead)
- **50-100x cheaper** (one instance vs 50)
- **Much simpler** (no orchestration needed)

