## 📋 Marker PDF OCR Skill — 审计报告

### 🎯 审计范围

**审计对象**: Marker PDF OCR Skill 开发规划 (SPEC.yaml + findings.md + task_plan.md)  
**审计类型**: TDD+SDD 设计方案审计  
**风险等级**: 🟡 Medium (新 Skill 开发,涉及外部 API 和本地资源管理)

---

### ✅ 优点总结

1. **研究工作扎实**: findings.md 对比了多种部署模式,清晰识别了 8GB RAM 的限制
2. **架构设计合理**: SPEC.yaml 采用 multi-modal 架构,支持 cloud/local/hybrid 多种模式
3. **契约清晰**: 接口定义 (MarkerOCRService, CloudAPIClient, LocalProcessor) 包含完整的前置/后置条件
4. **测试覆盖全面**: 包含 unit/integration/E2E 三层测试,场景覆盖 failover/resource-constraint
5. **文档结构符合 OpenClaw 规范**: 计划使用 SKILL.md + metadata 格式

---

### ❌ 关键问题

#### 🔴 P0 问题 (阻塞性,必须解决)

**问题 1: SPEC.yaml 不是 OpenClaw Skill 的必需文件**

- **现象**: 当前计划将 SPEC.yaml 作为核心设计文档,但 OpenClaw Skill 的**唯一必需文件**是 `SKILL.md`
- **根本原因**: 对 OpenClaw Skills 格式理解有偏差
- **正确做法**: 
  - `SKILL.md` 才是 OpenClaw 加载技能的入口
  - SPEC.yaml 可以作为内部开发文档,但不会被 OpenClaw 系统读取
  - 必须将 SPEC.yaml 中的关键信息提取到 `SKILL.md` 的 frontmatter 和正文中

**问题 2: 缺少 SKILL.md 的实际编写计划**

- **现象**: task_plan.md 列出了 6 个 Phase,但没有一个 Phase 是"编写 SKILL.md"
- **影响**: 即使测试框架完成,OpenClaw 也无法加载这个 Skill
- **建议**: 在 Phase 6 和 Phase 7 之间插入新 Phase:
  ```
  Phase 6.5: 编写 SKILL.md
  - 基于 SPEC.yaml 提取核心信息
  - 编写 frontmatter (metadata.openclaw)
  - 编写 Skill 使用说明
  - 定义环境变量要求 (DATLAB_API_KEY 等)
  ```

**问题 3: metadata.openclaw 定义缺失**

OpenClaw 依赖 `metadata.openclaw` 来判断 Skill 是否可用。当前规划中缺少:
```yaml
metadata:
  openclaw:
    requires:
      env: ["DATLAB_API_KEY"]  # Cloud mode 需要
      bins: []  # Local mode 需要什么二进制?
    primaryEnv: "DATLAB_API_KEY"
    install: []  # 如何安装依赖?
```

**建议补充**:
```yaml
metadata:
  openclaw:
    requires:
      env: ["DATLAB_API_KEY"]  # 可选,auto mode 会 fallback
      # bins: ["marker_single"]  # 如果 local_cpu mode 需要
    primaryEnv: "DATLAB_API_KEY"
    install:
      - id: "pip-marker"
        kind: "download"  # 或使用 pip installer (需验证)
        label: "Install marker-pdf via pip"
        # ... 具体安装命令
```

---

#### 🟡 P1 问题 (重要,应解决)

**问题 4: 缺少 OpenClaw 工具注册机制**

- **现状**: SPEC.yaml 定义了 Python 类接口 (MarkerOCRService),但没说明如何暴露给 OpenClaw agent
- **OpenClaw 工具系统**: Skill 需要通过某种方式让 agent 调用,常见方式:
  1. **CLI 工具** (最常见): Skill 描述一个命令行工具,agent 通过 `exec` 调用
  2. **HTTP API**: 提供本地 API,agent 通过 HTTP 调用
  3. **Python 库**: 如果 agent 运行在支持 Python 的环境

- **当前方案问题**: 
  - 如果做成 Python 库,OpenClaw agent (Node.js) 无法直接调用
  - 如果做成 CLI,需要明确 CLI 接口设计

**建议方案 A (CLI 工具,推荐)**:
```bash
# SKILL.md 中应描述:
marker-ocr convert <pdf_path> --output-format markdown --mode auto
marker-ocr health-check
marker-ocr get-mode-info
```

**建议方案 B (HTTP API,复杂度高)**:
```bash
# 启动服务
marker-ocr serve --port 8765

# Agent 通过 HTTP 调用
curl -X POST http://localhost:8765/convert \
  -F "file=@document.pdf" \
  -F "output_format=markdown"
```

**问题 5: 依赖安装流程不明确**

findings.md 提到:
> Previous Attempt: Model download failed due to memory constraints

但 task_plan.md 没有明确的依赖安装阶段。建议补充:
```markdown
Phase 0: 环境准备与依赖安装
- [ ] 验证 Python 版本 (>=3.8)
- [ ] 安装核心依赖 (requests, pydantic, pypdf)
- [ ] 可选: 安装 marker-pdf (local mode)
- [ ] 可选: 安装 torch (local mode, 但需注意内存)
- [ ] 验证 DATLAB_API_KEY (cloud mode)
```

**问题 6: Skill 可调用性 (user-invocable) 未定义**

SPEC.yaml 没有明确这个 Skill 是:
- `user-invocable: true` — 用户可以通过 `/marker-ocr` 命令直接调用
- `user-invocable: false` — 只能由 model 在需要时调用

**建议**: 设为 `user-invocable: true`,让用户可以主动触发 PDF 转换

---

#### 🟢 P2 问题 (改进建议,可选)

**问题 7: Token 开销分析缺失**

根据 OpenClaw 文档,Skill 列表会被注入到 system prompt,开销为:
```
total = 195 + (97 + len(name) + len(description) + len(location)) per skill
```

**当前 description**:
```yaml
description: "OpenClaw Skill for PDF to Markdown OCR conversion using Marker API with flexible deployment options (cloud, on-premise, or hybrid)"
```
长度: 139 字符

**建议精简**:
```yaml
description: "Convert PDF to Markdown using Marker OCR (cloud or local modes)"
```
长度: 66 字符 (节省 ~73 字符 ≈ 18 tokens)

**问题 8: 错误处理粒度不够细**

SPEC.yaml 定义了 `retryable: boolean`,但 findings.md 提到:
- Cloud API 可能返回 429 (rate limit)
- 需要读取 `Retry-After` header

**建议补充错误分类**:
```python
class ErrorClassification:
    RETRYABLE_TRANSIENT = ["429", "503", "network_timeout"]
    RETRYABLE_WITH_BACKOFF = ["rate_limit"]
    NOT_RETRYABLE = ["401", "invalid_file", "file_too_large"]
    REQUIRES_MODE_SWITCH = ["insufficient_memory", "api_quota_exceeded"]
```

---

### 🔧 具体修复建议

#### 修复 P0 问题的行动清单

**Action 1: 创建 SKILL.md 草稿**

```markdown
---
name: marker-pdf-ocr
description: Convert PDF to Markdown using Marker OCR (cloud or local modes)
user-invocable: true
metadata:
  {
    "openclaw": {
      "requires": {
        "env": ["DATLAB_API_KEY"]
      },
      "primaryEnv": "DATLAB_API_KEY",
      "install": [
        {
          "id": "pip-core",
          "kind": "node",  # 或 download
          "label": "Install marker-ocr dependencies",
          "bins": ["marker-ocr"]
        }
      ]
    }
  }
---

# Marker PDF OCR

Convert PDF documents to Markdown with high accuracy using Marker OCR.

## Usage

Convert a PDF file:
```bash
marker-ocr convert /path/to/document.pdf --output-format markdown
```

Check system health:
```bash
marker-ocr health-check
```

## Deployment Modes

- **Cloud API** (default): Uses Datalab.to API, requires `DATLAB_API_KEY`
- **Local CPU**: Processes on-premise, slower but private
- **Auto**: Automatically selects best mode based on available resources

## Environment Variables

- `DATLAB_API_KEY` (required for cloud mode): API key from datalab.to
- `MARKER_DEPLOYMENT_MODE` (optional): Force specific mode (cloud, local_cpu, auto)
- `MARKER_OCR_ENGINE` (optional, local mode): OCR engine (surya, ocrmypdf, tesseract)

## Requirements

- Python >= 3.8
- 8GB RAM minimum (cloud mode: 512MB, local mode: 4GB)
- For local mode: `pip install marker-pdf torch`

## Examples

Process with specific mode:
```bash
MARKER_DEPLOYMENT_MODE=cloud marker-ocr convert paper.pdf
```

Batch processing:
```bash
for f in *.pdf; do marker-ocr convert "$f"; done
```
```

**Action 2: 明确 CLI 接口设计**

在 SPEC.yaml 或新文档中补充:
```yaml
cli_interface:
  commands:
    - name: "convert"
      args:
        - name: "pdf_path"
          required: true
          type: "file_path"
        - name: "--output-format"
          type: "choice"
          choices: ["markdown", "json", "html", "chunks"]
          default: "markdown"
        - name: "--mode"
          type: "choice"
          choices: ["auto", "cloud", "local_cpu"]
          default: "auto"
      
      output:
        success: 
          stdout: "# Markdown content\n..."
          exit_code: 0
        failure:
          stderr: "Error: File not found\n"
          exit_code: 1
    
    - name: "health-check"
      output:
        format: "json"
        schema:
          healthy: "boolean"
          available_modes: "array"
          recommended_mode: "string"
```

**Action 3: 更新 task_plan.md**

```markdown
## Phase 6.5: 编写 SKILL.md 和 CLI 接口 (NEW)

### Actions
- [x] 创建 SKILL.md 基于 SPEC.yaml
- [x] 定义 metadata.openclaw (requires, install)
- [x] 编写 CLI 命令规范
- [x] 实现 CLI wrapper (调用 MarkerOCRService)
- [x] 测试 CLI 可被 OpenClaw exec 工具调用

### 产出
- `/root/.openclaw/workspace/skills/marker-pdf-ocr/SKILL.md`
- `/root/.openclaw/workspace/skills/marker-pdf-ocr/cli.py` (CLI 入口)
- `/root/.openclaw/workspace/skills/marker-pdf-ocr/setup.py` or `pyproject.toml`
```

---

### 📊 决策矩阵

| 问题 | 优先级 | 预计工作量 | 建议行动 |
|------|--------|-----------|----------|
| 缺少 SKILL.md | P0 | 2-4h | 立即编写 |
| metadata.openclaw 未定义 | P0 | 1h | 补充到 SKILL.md |
| CLI 接口未设计 | P0 | 4-6h | 设计 + 实现 CLI wrapper |
| 依赖安装流程不明 | P1 | 2h | 补充 Phase 0 |
| user-invocable 未定义 | P1 | 10min | 设为 true |
| Token 开销优化 | P2 | 30min | 精简 description |
| 错误分类细化 | P2 | 2h | 补充 ErrorClassification |

---

### 🎯 下一步行动建议

#### 立即执行 (今天)

1. **暂停 Phase 6 (测试框架生成)**,优先完成:
   - 编写 `SKILL.md` 初稿
   - 定义 CLI 接口规范
   - 确认 metadata.openclaw 配置

2. **与 Main Agent 确认**:
   - 是否采用 CLI 工具模式 (vs HTTP API)?
   - Skill 名称确认: `marker-pdf-ocr` 还是 `pdf-ocr`?
   - 是否需要支持 user-invocable?

#### 本周完成

3. **重新排序开发阶段**:
   ```
   Phase 0: 环境准备 (NEW)
   Phase 1-5: (已完成)
   Phase 6: CLI 接口实现 (MODIFIED)
   Phase 6.5: SKILL.md 编写 (NEW)
   Phase 7: 测试框架生成 (MOVED)
   Phase 8: 部署文档 (MOVED)
   ```

4. **完成 P0/P1 问题修复**

5. **验证 OpenClaw 加载**:
   ```bash
   # 测试 Skill 是否被正确加载
   openclaw gateway call --help
   # 查看 skills 列表
   ```

---

### 📝 总结

**当前状态**: 🟡 需要重大修正

**核心问题**: 设计文档(SPEC.yaml)很完善,但**忽略了 OpenClaw Skill 的实际接入方式**。SPEC.yaml 定义的是 Python 类接口,但 OpenClaw 需要的是:
1. `SKILL.md` 文件 (必需)
2. 可执行的工具 (CLI/API)
3. metadata 配置 (依赖检查)

**建议路径**:
- 保留 SPEC.yaml 作为内部设计文档
- 但**必须**创建 SKILL.md 作为 OpenClaw 入口
- 实现 CLI wrapper 暴露功能给 agent

**预计额外工作量**: 1-2 天 (编写 SKILL.md + CLI wrapper + 调试 OpenClaw 集成)

---

### 💬 反馈给 Galatea 的建议

```markdown
## Audit Result for Marker PDF OCR Skill

### ✅ Great Work On:
- Comprehensive research (findings.md)
- Well-structured SPEC.yaml with clear contracts
- Multi-modal architecture design

### ❌ Critical Issues (Must Fix):

1. **Missing SKILL.md**: OpenClaw requires `SKILL.md` as the entry point. SPEC.yaml alone won't work.
   - Action: Create `SKILL.md` with frontmatter + usage instructions
   - Include `metadata.openclaw` for dependency checking

2. **No CLI Interface**: SPEC.yaml defines Python classes, but OpenClaw agents need executable tools.
   - Action: Implement CLI wrapper (`marker-ocr convert`, `marker-ocr health-check`)
   - Make it callable via OpenClaw's `exec` tool

3. **Missing metadata.openclaw**:
   ```yaml
   metadata:
     openclaw:
       requires:
         env: ["DATLAB_API_KEY"]
       primaryEnv: "DATLAB_API_KEY"
   ```

### 📋 Revised Phase Plan:

Insert new phases:
- **Phase 0**: Dependency installation strategy
- **Phase 6.5**: Write SKILL.md + implement CLI wrapper
- Move test generation to Phase 7

### 🔗 References:
- OpenClaw Skills format: https://docs.openclaw.ai/tools/skills
- SKILL.md examples: Check bundled skills in `~/.openclaw/skills`
- CLI tool pattern: See `gemini` skill for reference

### Next Steps:
1. Pause test framework generation
2. Create SKILL.md draft (I can provide a template)
3. Design CLI interface (args, output format)
4. Confirm: CLI tool or HTTP API?
```

---