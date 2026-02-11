# Task Plan - Marker PDF OCR Skill (TDD+SDD)

> Session: pdf-ocr-design  
> Date: 2026-02-08  
> Status: UPDATED after Master Review & Claude Audit

---

## 🎯 Updated Strategy (Post-Audit)

**Key Changes Based on Audit & Master Feedback:**

1. ✅ **Local-First Strategy** - With 23GB swap configured, local mode is now primary
2. ✅ **CLI Interface Added** - OpenClaw needs executable tools, not just Python classes
3. ✅ **SKILL.md Created** - Required for OpenClaw integration
4. ✅ **Metadata.openclaw Defined** - For dependency checking and install flow
5. ⏳ **Implementation Phase Reordered** - CLI before test framework

---

## Phase Overview (UPDATED)

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | ✅ Complete | Environment prep (swap configured: 23GB) |
| Phase 1 | ✅ Complete | Research Marker projects |
| Phase 2 | ✅ Complete | Initialize TDD+SDD structure |
| Phase 3 | ✅ Complete | Write SPEC.yaml (local-first architecture) |
| Phase 4 | ✅ Complete | Create findings.md |
| Phase 5 | ✅ Complete | Create task_plan.md |
| Phase 6 | ✅ Complete | **Write SKILL.md** (NEW - required for OpenClaw) |
| Phase 7 | ✅ Complete | **Design CLI interface** (NEW - OpenClaw integration) |
| Phase 8 | ✅ Complete | **Implement CLI wrapper** (NEW - exec tool callable) |
| Phase 9 | ✅ Complete | Implement core service logic |
| Phase 10 | 🔄 Ready | Generate test framework (subagent) |
| Phase 11 | ⏳ Pending | Integration testing |
| Phase 12 | ⏳ Pending | Write deployment documentation |

---

## Phase 0: Environment Prep (COMPLETED)

### Actions Taken
- [x] Master configured 23GB swap file
- [x] Verified swap activation: `free -h` shows 23GB swap
- [x] Memory pressure eliminated

### Impact
- **Local CPU mode now viable** - Was marginal at 8GB RAM, now safe with 23GB swap
- **Strategy shifted** - From "cloud-first" to "local-first"
- **Privacy preserved** - PDFs stay on-premise by default

---

## Phase 1-5: Research & Design (COMPLETED)

See original task_plan.md for details.

**Key Decisions Updated:**
- Primary mode: **local_cpu** (was cloud_api)
- Fallback mode: **cloud_api**
- GPU mode: Still excluded (no GPU available)

---

## Phase 6: Write SKILL.md (COMPLETED)

### Actions Taken
- [x] Create `SKILL.md` with frontmatter metadata
- [x] Define `metadata.openclaw` structure
- [x] Write usage examples
- [x] Document environment variables
- [x] Add installation instructions

### Output
- File: `/root/.openclaw/workspace/skills/marker-pdf-ocr/SKILL.md`
- Size: ~4.8KB
- Contains: frontmatter, usage, modes, examples, troubleshooting

### Metadata Structure
```yaml
metadata:
  openclaw:
    requires:
      env: ["MARKER_API_KEY"]
      bins: ["python3"]
      minRamMb: 512
    primaryEnv: "MARKER_API_KEY"
    install: [...]
```

---

## Phase 7: Design CLI Interface (COMPLETED)

### Actions Taken
- [x] Define CLI commands (`convert`, `health-check`, `install-local`)
- [x] Design argument structure
- [x] Define output formats (JSON for programmatic use)
- [x] Document exit codes
- [x] Add to SPEC.yaml `cli_interface` section

### CLI Commands
| Command | Purpose | Exit Code |
|---------|---------|-----------|
| `convert` | Convert PDF to Markdown | 0=success, 1=failure |
| `health-check` | Check system health | 0=healthy, 1=unhealthy |
| `install-local` | Install local dependencies | 0=success, 1=failure |

---

## Phase 8: Implement CLI Wrapper (COMPLETED)

### Actions Taken
- [x] Create `tools/marker-ocr.py` CLI entry point
- [x] Implement argument parsing with argparse
- [x] Add command routing logic
- [x] Implement error handling with JSON output
- [x] Add user-friendly error suggestions

### Output
- File: `/root/.openclaw/workspace/skills/marker-pdf-ocr/tools/marker-ocr.py`
- Size: ~5.5KB
- Executable: Yes (`chmod +x` ready)

### CLI Usage Examples
```bash
# Convert PDF (auto mode)
python3 tools/marker-ocr.py convert paper.pdf

# Force local mode
python3 tools/marker-ocr.py convert paper.pdf --mode local

# Check health
python3 tools/marker-ocr.py health-check --verbose

# Install dependencies
python3 tools/marker-ocr.py install-local --yes
```

---

## Phase 9: Implement Core Service Logic (IN PROGRESS)

### Actions Taken
- [x] Create `lib/marker_ocr_service.py` framework
- [x] Define `MarkerOCRService` class
- [x] Implement mode selection logic (auto → local → cloud)
- [x] Add health check functionality
- [x] Define error classification

### Pending Implementation
- [ ] Actual marker-pdf integration (local mode)
- [ ] Datalab.to API integration (cloud mode)
- [ ] File validation and sanitization
- [ ] Progress reporting for long operations

### Output
- File: `/root/.openclaw/workspace/skills/marker-pdf-ocr/lib/marker_ocr_service.py`
- Size: ~6.9KB
- Status: Framework complete, core logic stubbed

---

## Phase 10: Generate Test Framework (PENDING)

### Planned Actions
- [ ] Generate unit tests from SPEC.yaml interfaces
- [ ] Create integration tests for failover logic
- [ ] Write acceptance tests for E2E scenarios
- [ ] Add test fixtures and mocks

### Test Coverage Target
- Unit tests: 85% coverage
- Integration tests: All mode transitions
- Acceptance tests: 4 E2E scenarios from SPEC

---

## Phase 11: Integration Testing (PENDING)

### Planned Actions
- [ ] Test CLI execution via OpenClaw `exec` tool
- [ ] Verify SKILL.md metadata parsing
- [ ] Test mode failover under resource pressure
- [ ] Validate error handling and reporting

---

## Phase 12: Documentation (PENDING)

### Planned Actions
- [ ] Write deployment guide
- [ ] Add troubleshooting section
- [ ] Create usage examples
- [ ] Document cloud API costs

---

## 📁 Current Project Structure

```
/root/.openclaw/workspace/skills/marker-pdf-ocr/
├── SKILL.md                      # ✅ OpenClaw entry point
├── SPEC.yaml                     # ✅ Updated with local-first strategy
├── README.md                     # ✅ User documentation
├── task_plan.md                  # ✅ This file
├── findings.md                   # ✅ Research findings
├── requirements.txt              # ✅ Python dependencies
├── pytest.ini                    # ✅ Test configuration
├── .gitignore                    # ✅ Git ignore rules
│
├── lib/
│   ├── __init__.py               # ✅ Package marker
│   └── marker_ocr_service.py     # ✅ Core service (14KB, full impl)
│
├── tools/
│   └── marker-ocr.py             # ✅ CLI tool (9.6KB, executable)
│
└── tests/                        # 🔄 Pending implementation
    ├── __init__.py
    ├── unit/
    ├── integration/
    └── acceptance/
```

---

## Phase 9: Implement Core Service Logic (COMPLETED)

### Actions Taken
- [x] Implement `marker-pdf` integration for local mode
  - Subprocess call to `marker.scripts.convert_single`
  - CPU-only mode with `--force_cpu`
  - Single worker to control memory (`--max_workers 1`)
  - Automatic cleanup of temp directories
- [x] Implement Datalab.to API integration for cloud mode
  - File upload with multipart/form-data
  - Async polling for results
  - Proper error handling (rate limits, auth errors)
- [x] Add robust error handling and classification
  - `ErrorClassification` class for retry logic
  - Mode switch suggestions on failures
  - User-friendly error messages with suggestions
- [x] Update CLI with actual service calls
  - Rich output formatting
  - Progress indicators
  - Helpful error messages

### Implementation Details

**Local Mode (`_convert_local`)**:
- Uses `python3 -m marker.scripts.convert_single`
- Creates temp directory for output
- Parses markdown/json output
- Cleans up temp files after conversion
- Handles MemoryError with helpful suggestions

**Cloud Mode (`_convert_cloud`)**:
- POST to `https://www.datalab.to/api/v1/convert`
- Polls `/result/{request_id}` for completion
- Exponential backoff (2s → 10s max)
- Returns content + metadata

**Health Check**:
- Checks marker-pdf availability via import test
- Calculates available memory (RAM + swap)
- Determines recommended mode
- Reports both local and cloud readiness

### Output Files
- `lib/marker_ocr_service.py` - 14KB, full implementation
- `tools/marker-ocr.py` - 9.6KB, CLI with rich output

---

## 🎯 Next Immediate Actions

1. **Test CLI manually** (Ready to test)
   ```bash
   # Health check
   python3 tools/marker-ocr.py health-check --verbose
   
   # Convert with available mode
   python3 tools/marker-ocr.py convert test.pdf --mode auto
   ```

2. **Generate test framework** (Assign to subagent)
   ```bash
   python3 ~/.openclaw/workspace/skills/tdd-sdd-skill/lib/test_generator.py \
     --spec SPEC.yaml --output tests/
   ```

3. **Test CLI via OpenClaw exec** (Assign to subagent)
   - Verify SKILL.md metadata parsing
   - Test exec tool invocation
   - Validate error handling

---

## 📝 Notes

### Master Requirements (Updated)
- ✅ 23GB swap configured - local mode now viable
- ✅ Local-first strategy - minimize cloud API costs
- ✅ LLM calls excepted - use existing providers
- ⏳ Awaiting Master approval on current implementation before proceeding

### Blockers
- None currently

### Resources
- Skill path: `~/.openclaw/workspace/skills/marker-pdf-ocr/`
- TDD+SDD skill: `~/.openclaw/workspace/skills/tdd-sdd-skill/`
- OpenClaw docs: https://docs.openclaw.ai/tools/skills

---

*Last updated: 2026-02-08 21:45 UTC*
