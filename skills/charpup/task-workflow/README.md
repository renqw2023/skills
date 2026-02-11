# OpenClaw Task Workflow

Standardized Planning + Subagent + Progress Report workflow for complex tasks in OpenClaw.

## Overview

This skill provides structured templates for task planning, subagent dispatch, progress tracking, and result integration. It ensures consistent execution of complex multi-step tasks (>5 tool calls or >10 minutes).

## Features

- **Structured Planning**: Task decomposition with time estimation
- **Parallel Execution**: Subagent dispatch for concurrent processing
- **Progress Tracking**: Automated 5-minute interval reporting
- **Result Integration**: Unified report generation

## When to Use

Use this workflow when tasks meet any of these criteria:
- Expected >5 tool calls
- Execution time >10 minutes
- Requires parallel processing
- Involves subagent collaboration

## Quick Start

```bash
# Initialize task planning
bash ~/.openclaw/skills/planning-with-files/scripts/init-session.sh

# Create task plan
cat > task_plan.md << 'EOF'
# Task Plan - [Task Name]

**Start Time**: YYYY-MM-DD HH:MM
**Estimated Duration**: XX minutes
**Report Interval**: 5 minutes

## Batches

| Batch | Task | Assignee | Est. Time | Status |
|-------|------|----------|-----------|--------|
| 1 | [Task] | subagent-1 | 5min | ⏳ |
| 2 | [Task] | subagent-2 | 5min | ⏳ |

## Progress Tracking

| Time | Batch | Status | Notes |
|------|-------|--------|-------|
| HH:MM | 1 | ✅ | Complete |
EOF

# Dispatch subagents
openclaw sessions_spawn --label "batch-1" --task "..."
openclaw sessions_spawn --label "batch-2" --task "..."

# Set up progress reporting
openclaw cron add --name "progress-tracker" \
  --every 300000 \
  --message "Check task_plan.md and report progress"
```

## Workflow Steps

### Step 1: Planning (2-3 min)
- Create `task_plan.md`
- Split into parallel batches
- Estimate time for each batch

### Step 2: Subagent Dispatch
- Dispatch independent subagents per batch
- Main agent stays responsive
- Set appropriate timeouts

### Step 3: Progress Tracking
- Automatic 5-minute reports
- Update `task_plan.md` progress
- Alert on anomalies

### Step 4: Integration & Report
- Collect subagent results
- Generate unified report
- Update MEMORY.md

## Templates

See `templates/task-plan.md` for the full task plan template.

See `examples/example-task.md` for a complete example.

## Integration with AGENTS.md

Add this to your AGENTS.md:

```markdown
## Task Execution Workflow

> **Updated**: Use for complex tasks (>5 tool calls)

### Standard Process
1. **Planning**: Create task_plan.md
2. **Dispatch**: Parallel subagents
3. **Tracking**: 5-min progress reports
4. **Integration**: Unified report

**Reference**: `skills/task-workflow/SKILL.md`
```

## Benefits

- **Predictability**: Clear task structure
- **Parallelism**: Faster execution via subagents
- **Visibility**: Regular progress updates
- **Reliability**: Standardized error handling

## Version

- **Current**: 1.0.0
- **OpenClaw**: 2026.2.1+

## License

MIT
