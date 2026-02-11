# Marker PDF OCR - Deployment Findings

> Research findings for TDD+SDD PDF OCR Skill Design  
> Date: 2026-02-08  
> Author: OpenClaw SubAgent  

---

## Executive Summary

This document summarizes research findings for deploying Marker PDF OCR in an **8GB RAM + 24GB Swap** environment. The conclusion is clear: **avoid local LLM deployment** and use either the **hosted cloud API** or **CPU-only local processing**.

---

## 1. Marker Ecosystem Overview

### Two Main Projects

| Project | Repository | Purpose |
|---------|------------|---------|
| **marker** | `datalab-to/marker` | Core PDF-to-Markdown library |
| **marker-api** | `adithya-s-k/marker-api` | FastAPI wrapper with distributed support |

### Key Features

- **Input formats**: PDF, images, PPTX, DOCX, XLSX, HTML, EPUB
- **Output formats**: Markdown, JSON, HTML, Chunks (for RAG)
- **OCR engines**: Surya (default), OCRMyPDF, Tesseract
- **Optional LLM enhancement**: Gemini, Claude, OpenAI, Ollama, Azure
- **Language support**: All languages (with appropriate OCR engine)

---

## 2. Resource Requirements Analysis

### Official Requirements

| Mode | RAM | VRAM | Storage | Notes |
|------|-----|------|---------|-------|
| **GPU Mode** | 8GB+ | 4-5GB | 10GB | **NOT SUITABLE** for 8GB host |
| **CPU Mode** | 4GB+ | N/A | 5GB | Acceptable with swap |
| **Cloud API** | 512MB | N/A | 1GB | **RECOMMENDED** |

### Critical Findings for 8GB Host

```
⚠️  8GB RAM is INSUFFICIENT for GPU mode:
   - Marker requires ~4-5GB VRAM per worker
   - System RAM + VRAM contention causes OOM
   - LLM models (for --use_llm) add additional 2-4GB

✅  8GB RAM is SUFFICIENT for:
   - Cloud API mode (minimal local resources)
   - CPU-only local processing (with swap)
   - Hybrid mode (local OCR + cloud LLM)
```

### Memory Usage Breakdown

| Component | GPU Mode | CPU Mode | Cloud Mode |
|-----------|----------|----------|------------|
| Base OS | 1-2GB | 1-2GB | 1-2GB |
| Marker models | 4-5GB VRAM | 2-3GB RAM | N/A |
| LLM (optional) | 2-4GB VRAM | N/A | N/A |
| Processing overhead | 1GB | 1-2GB | 256MB |
| **Total Required** | **8-12GB** | **4-7GB** | **~512MB** |
| **With 8GB Host** | ❌ OOM Risk | ⚠️ With swap | ✅ Optimal |

---

## 3. Deployment Options Comparison

### Option 1: Datalab.to Hosted API (RECOMMENDED)

**Description**: Use the official managed API service

**Pros**:
- ✅ Minimal local resources (~512MB RAM)
- ✅ No GPU required
- ✅ 99.99% uptime SLA
- ✅ Fast: ~15s for 250-page PDF
- ✅ LLM enhancement available
- ✅ Scales automatically

**Cons**:
- ❌ Data leaves premises
- ❌ Per-page API costs (~$0.001-0.01/page estimated)
- ❌ Requires internet connection
- ❌ Rate limits apply

**Cost Estimate**:
```
Light usage (100 pages/day): ~$3-10/month
Medium usage (1000 pages/day): ~$30-100/month
Heavy usage (10000 pages/day): ~$300-1000/month
```

**Setup**:
```bash
export DATLAB_API_KEY="your_api_key"
# No local installation required
```

---

### Option 2: Local CPU Processing

**Description**: Run marker-pdf without GPU acceleration

**Pros**:
- ✅ No data leaves premises
- ✅ One-time cost (no ongoing API fees)
- ✅ Works offline
- ✅ No rate limits

**Cons**:
- ❌ Slower: ~2-5s per page (vs ~0.6s with GPU)
- ❌ No LLM enhancement (--use_llm disabled)
- ❌ Requires 4GB+ RAM + swap on 8GB host
- ❌ Higher CPU usage

**Performance**:
```
Single page: 2-5 seconds
10-page document: 20-50 seconds
50-page document: 2-4 minutes
```

**Setup**:
```bash
pip install marker-pdf
marker_single /path/to/file.pdf
```

**Configuration for 8GB Host**:
```bash
# Force CPU mode
export TORCH_DEVICE=cpu
export INFERENCE_RAM=4
export VRAM_PER_TASK=4

# Disable LLM (requires GPU)
# Do not use --use_llm flag
```

---

### Option 3: Docker CPU Mode

**Description**: Containerized marker-api with CPU-only support

**Pros**:
- ✅ Isolated environment
- ✅ Easy setup with docker-compose
- ✅ Includes Celery for task queuing
- ✅ Flower monitoring included

**Cons**:
- ❌ Container overhead (~1-2GB additional RAM)
- ❌ Docker daemon required
- ❌ More complex than direct library usage
- ❌ No GPU support in container on 8GB host

**Resource Requirements**:
```
RAM: 6GB+ (with container overhead)
Storage: 10GB+
Docker: 20.0+
```

**Setup**:
```bash
docker build -f docker/Dockerfile.cpu.server -t marker-api-cpu .
docker run -p 8080:8080 marker-api-cpu
```

**Note**: On 8GB host, this leaves very little headroom. **Not recommended** unless strictly necessary.

---

### Option 4: Hybrid Mode (Experimental)

**Description**: Local preprocessing + Cloud LLM enhancement

**Pros**:
- ✅ Balance of privacy and accuracy
- ✅ Lower cloud costs (text vs full PDF)
- ✅ Reduced bandwidth usage

**Cons**:
- ❌ Complex setup
- ❌ Two failure points
- ❌ Partial data sharing (text only)

**Use Case**: Extract text locally, send only text to LLM for formatting.

---

## 4. Deployment Decision Matrix

| Factor | Cloud API | Local CPU | Docker CPU |
|--------|-----------|-----------|------------|
| **8GB RAM Suitability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Privacy** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Speed** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Cost (Low Volume)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Cost (High Volume)** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Setup Complexity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Offline Capability** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **LLM Enhancement** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ |

**Recommendation for 8GB Host**: 
1. **Primary**: Cloud API mode (get DATLAB_API_KEY)
2. **Fallback**: Local CPU mode (for offline/privacy needs)

---

## 5. Historical Context: Why Previous Deployment Failed

### Previous Attempt
- **Approach**: Local LLM deployment on 8GB RAM host
- **Issue**: Model download failed due to memory constraints
- **Root Cause**: 
  - Marker models: ~2-3GB download
  - PyTorch + dependencies: ~2GB
  - LLM model (optional): ~4GB
  - **Total**: ~8GB+ exceeds available RAM during download/install

### Lessons Learned
1. **Pre-check available memory** before attempting model downloads
2. **Use swap space** for installation if local mode required
3. **Consider cloud API** for resource-constrained environments
4. **Incremental model loading** instead of all-at-once

---

## 6. Recommended Architecture for 8GB Host

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw Skill Interface                 │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
            ┌──────────┐     ┌──────────┐
            │  Cloud   │     │  Local   │
            │   API    │◄────┤   CPU    │
            │  Mode    │     │   Mode   │
            └────┬─────┘     └────┬─────┘
                 │                │
            ┌────┴────┐      ┌────┴────┐
            │Datalab.to│      │marker- │
            │   API    │      │  pdf   │
            └──────────┘      └────────┘
```

### Failover Strategy

```python
# Auto mode selection logic
def select_mode(pdf_size_mb, available_ram_gb, api_key_available):
    if api_key_available and available_ram_gb < 4:
        return "cloud"  # Insufficient RAM for local
    elif api_key_available:
        return "cloud"  # Cloud is faster, use it
    elif available_ram_gb >= 4:
        return "local_cpu"  # Fallback to CPU mode
    else:
        raise ResourceError("Insufficient resources. Add DATLAB_API_KEY.")
```

---

## 7. Configuration Recommendations

### For Cloud Mode (Recommended)
```yaml
environment:
  MARKER_DEPLOYMENT_MODE: "cloud"
  DATLAB_API_KEY: "${DATLAB_API_KEY}"
  MARKER_FAILOVER_ENABLED: "true"
```

### For Local CPU Mode (Fallback)
```yaml
environment:
  MARKER_DEPLOYMENT_MODE: "local_cpu"
  TORCH_DEVICE: "cpu"
  INFERENCE_RAM: "4"
  MARKER_OCR_ENGINE: "surya"  # or "ocrmypdf"
  MARKER_MAX_WORKERS: "1"
```

### For Swap Optimization (if using local mode)
```bash
# Check current swap
free -h

# Add swap if needed (for 8GB host, add 8-16GB swap)
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 8. Testing Recommendations

### Unit Tests
- Mock cloud API responses
- Test mode selection logic
- Validate error handling

### Integration Tests
- Test with Datalab.to sandbox
- Test local marker-pdf integration
- Verify failover behavior

### Load Tests
- Memory usage under load (8GB limit)
- Swap usage monitoring
- API rate limit handling

---

## 9. References

- **Marker Core**: https://github.com/datalab-to/marker
- **Marker API**: https://github.com/adithya-s-k/marker-api
- **Datalab.to**: https://www.datalab.to
- **PyPI**: https://pypi.org/project/marker-pdf/

---

## 10. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-08 | Exclude GPU mode | 8GB host insufficient for 4-5GB VRAM + system overhead |
| 2026-02-08 | Prioritize cloud API | Best balance of performance/resource usage for 8GB host |
| 2026-02-08 | Include CPU local mode | Fallback for offline/privacy requirements |
| 2026-02-08 | Exclude Docker CPU | Container overhead too high for 8GB host |

---

*Document generated as part of TDD+SDD PDF OCR Skill design process.*
