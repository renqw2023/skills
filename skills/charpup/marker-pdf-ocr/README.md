# Marker PDF OCR Skill

> OpenClaw Skill for PDF to Markdown OCR conversion  
> Built with TDD+SDD Dual Pyramid Process  

## Overview

This skill provides robust PDF OCR capabilities with multiple deployment options optimized for different resource constraints. It converts PDF documents to Markdown (or JSON/HTML) with high accuracy, supporting various OCR engines and optional LLM enhancement.

## Features

- **Multi-Modal Deployment**: Cloud API, Local CPU, Docker, or Hybrid modes
- **Automatic Failover**: Seamlessly switches between modes on errors
- **Resource Aware**: Optimized for 8GB RAM environments
- **High Accuracy**: Supports Surya, OCRMyPDF, and Tesseract OCR engines
- **Multiple Formats**: Output to Markdown, JSON, HTML, or Chunks (for RAG)

## Quick Start

```python
from marker_pdf_ocr import MarkerOCRService

# Initialize service
service = MarkerOCRService()

# Convert PDF (auto-detects best mode)
result = service.convert_pdf(
    pdf_path="/path/to/document.pdf",
    output_format="markdown"
)

if result["success"]:
    print(result["content"])
else:
    print(f"Error: {result['error']}")
```

## Deployment Modes

### 1. Cloud API Mode (Recommended for 8GB RAM)

Uses [Datalab.to](https://www.datalab.to) hosted API for processing.

**Requirements**: ~512MB RAM, API key  
**Pros**: Fast, no GPU needed, managed scaling  
**Cons**: Data leaves premises, API costs

```bash
export DATLAB_API_KEY="your_api_key"
export MARKER_DEPLOYMENT_MODE="cloud"
```

### 2. Local CPU Mode (Fallback)

Runs `marker-pdf` locally without GPU acceleration.

**Requirements**: 4GB+ RAM, 8GB+ swap recommended  
**Pros**: No data leaves premises, one-time cost  
**Cons**: Slower processing, no LLM enhancement

```bash
pip install marker-pdf
export MARKER_DEPLOYMENT_MODE="local_cpu"
export TORCH_DEVICE=cpu
```

### 3. Docker Mode (Not recommended for 8GB)

Uses containerized marker-api.

**Requirements**: 6GB+ RAM, Docker  
**Note**: Container overhead makes this unsuitable for 8GB hosts

### 4. Auto Mode (Default)

Automatically selects best mode based on available resources and configuration.

```bash
export MARKER_DEPLOYMENT_MODE="auto"
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATLAB_API_KEY` | For cloud mode | - | Datalab.to API key |
| `MARKER_DEPLOYMENT_MODE` | No | `auto` | Deployment mode: auto, cloud, local_cpu |
| `MARKER_OCR_ENGINE` | No | `surya` | OCR engine: surya, ocrmypdf, tesseract |
| `MARKER_OUTPUT_DIR` | No | `/tmp/marker_output` | Output directory |
| `MARKER_FAILOVER_ENABLED` | No | `true` | Enable automatic failover |
| `MARKER_MAX_RETRIES` | No | `3` | Max retry attempts |

### Mode Selection Logic

```
if mode == "auto":
    if DATLAB_API_KEY set:
        return "cloud"          # Preferred: fast, low resource
    elif marker-pdf installed and RAM >= 4GB:
        return "local_cpu"      # Fallback: private, offline
    else:
        raise ConfigurationError("No viable mode available")
```

## Resource Requirements

| Mode | RAM | Storage | GPU | Notes |
|------|-----|---------|-----|-------|
| Cloud | 512MB | 1GB | No | **Recommended for 8GB hosts** |
| Local CPU | 4GB+ | 5GB | No | Use swap for 8GB hosts |
| Docker | 6GB+ | 10GB | No | Not recommended for 8GB |
| GPU | 8GB+ | 10GB | 4GB+ | **Not suitable for 8GB host** |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              OpenClaw Skill Interface                   │
└─────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      ┌──────────────┐        ┌──────────────┐
      │ Orchestrator │        │ Health Check │
      └──────┬───────┘        └──────────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐
│ Cloud │ │ Local │ │Docker │
│  API  │ │  CPU  │ │ (opt) │
└───┬───┘ └───┬───┘ └───────┘
    │         │
    ▼         ▼
┌────────┐  ┌──────────┐
│Datalab │  │ marker-  │
│  .to   │  │  pdf     │
└────────┘  └──────────┘
```

## Testing

### Run All Tests

```bash
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

### Run by Category

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Acceptance tests (requires API key)
pytest tests/acceptance/ -v --cloud

# Specific mode tests
pytest -m cloud -v
pytest -m local_cpu -v
pytest -m failover -v
```

### Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.acceptance` - Acceptance tests
- `@pytest.mark.cloud` - Cloud API tests
- `@pytest.mark.local_cpu` - Local CPU tests
- `@pytest.mark.failover` - Failover tests
- `@pytest.mark.performance` - Performance tests

## Development

### TDD+SDD Process

This skill was developed using the TDD+SDD Dual Pyramid approach:

1. **Specification First**: `SPEC.yaml` defines all interfaces and contracts
2. **Test Generation**: Tests generated from SPEC.yaml scenarios
3. **Implementation**: Code written to pass tests
4. **Validation**: SPEC validated against implementation

### Project Structure

```
marker-pdf-ocr/
├── SPEC.yaml              # SDD specification
├── findings.md            # Deployment research
├── task_plan.md           # Development plan
├── README.md              # This file
├── lib/                   # Implementation
│   ├── __init__.py
│   └── marker_pdf_ocr/    # Main package
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── acceptance/        # E2E tests
│   └── conftest.py        # Test fixtures
└── requirements.txt       # Dependencies
```

## Troubleshooting

### "No viable deployment mode available"

**Cause**: Neither cloud API key nor local marker-pdf is available.

**Solutions**:
1. Set `DATLAB_API_KEY` for cloud mode
2. Install marker-pdf: `pip install marker-pdf`
3. Check available memory: `free -h`

### "Out of memory" during local processing

**Cause**: Insufficient RAM for marker-pdf.

**Solutions**:
1. Use cloud mode instead
2. Add swap space: `sudo fallocate -l 16G /swapfile`
3. Reduce `MARKER_MAX_WORKERS` to 1

### "API rate limit exceeded"

**Cause**: Too many requests to Datalab.to API.

**Behavior**: Skill automatically fails over to local CPU mode if available.

**Solutions**:
1. Wait for rate limit reset
2. Install marker-pdf for local fallback
3. Contact Datalab.to for higher limits

## Performance Benchmarks

| Mode | Single Page | 10 Pages | 50 Pages |
|------|-------------|----------|----------|
| Cloud | ~3s | ~15s | ~60s |
| Local CPU | ~5s | ~60s | ~5min |

*Benchmarks on 8GB RAM system with swap*

## License

This skill is part of the OpenClaw ecosystem. Refer to LICENSE file for details.

## References

- [Marker Core](https://github.com/datalab-to/marker) - Core PDF conversion library
- [Marker API](https://github.com/adithya-s-k/marker-api) - FastAPI wrapper
- [Datalab.to](https://www.datalab.to) - Hosted API service
