# Galatea Memory Manager 部署指南

## 快速部署

### 1. 创建符号链接 (推荐)

```bash
# 添加 CLI 到 PATH
sudo ln -sf /root/.openclaw/workspace/skills/galatea-memory/bin/memory-checkpoint /usr/local/bin/memory-checkpoint
sudo ln -sf /root/.openclaw/workspace/skills/galatea-memory/bin/memory-key-add /usr/local/bin/memory-key-add

# 验证
memory-checkpoint --help
memory-key-add --help
```

### 2. 配置 AGENTS.md

在 `/root/.openclaw/workspace/AGENTS.md` 中添加:

```markdown
## Memory Management Integration

### 会话开始时
```python
import sys
sys.path.insert(0, '/root/.openclaw/workspace/skills/galatea-memory')
from memory_manager import MemoryManager

mm = MemoryManager()
memories = mm.get_short_term_memories(limit=10)
checkpoints = mm.list_checkpoints()
```

### 处理用户消息时
```python
# 检测关键信息触发词
is_key, content = mm.detect_key_triggers(user_message)
if is_key:
    mm.mark_key_info(content)
```

### 任务完成时
```python
mm.auto_checkpoint_on_task_complete(task_description)
```

### 会话结束时
```python
mm.create_checkpoint(task="会话结束", context={'cache': mm.cache})
```
```

### 3. 可选: Heartbeat 集成

在 `HEARTBEAT.md` 中添加:

```markdown
- [ ] 检查是否需要创建检查点 (每 30 分钟)
- [ ] 归档旧的短期记忆条目
```

### 4. 可选: Notion 配置

设置环境变量:

```bash
export NOTION_API_KEY="your-notion-integration-token"
export NOTION_DATABASE_ID="your-database-id"
```

然后在 `memory_manager.py` 中取消 `_sync_to_notion` 方法的注释并完善实现。

## 使用示例

### 日常操作

```bash
# 1. 查看当前状态
memory-manager stats

# 2. 列出最近检查点
memory-checkpoint list

# 3. 创建检查点
memory-checkpoint create "完成用户模块" \
  -d "使用 JWT 认证" \
  -t "添加邮箱验证" "实现密码重置"

# 4. 添加关键信息
memory-key-add "服务器 IP: 192.168.1.100" -t #server #credential

# 5. 查看关键信息
memory-key-add list

# 6. 检测文本中的关键信息
memory-key-add detect "记住这个：明天开会"
```

### Python API 使用

```python
from memory_manager import MemoryManager, Priority

mm = MemoryManager()

# 短期记忆
mm.add_to_short_term("重要信息", priority=Priority.HIGH)
memories = mm.get_short_term_memories(limit=5)

# 检查点
checkpoint_id = mm.create_checkpoint(
    task="完成任务",
    decisions=["决策1", "决策2"],
    todos=["待办1", "待办2"]
)

# 关键信息
entry_id = mm.mark_key_info("重要内容", tags=["#health"])

# 自动触发
is_key, content = mm.detect_key_triggers("记住这个：xxx")
category, tags = mm.auto_classify(content)
```

## 故障排除

### 导入错误

```bash
# 确保正确导入
export PYTHONPATH="/root/.openclaw/workspace/skills/galatea-memory:$PYTHONPATH"
```

### 权限问题

```bash
chmod +x /root/.openclaw/workspace/skills/galatea-memory/bin/*
```

### 检查点不保存

确认目录存在:
```bash
mkdir -p /root/.openclaw/workspace/checkpoints
```

## 更新日志

### v1.0.0 (2026-02-05)
- ✅ 初始版本
- ✅ 分层记忆系统
- ✅ 自动检查点
- ✅ 关键信息标记
- ✅ CLI 工具

---

**部署状态**: ✅ 就绪
