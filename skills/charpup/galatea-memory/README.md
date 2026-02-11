# Galatea Memory Manager

Galatea 专属的记忆管理增强系统。

## 快速开始

```bash
# 创建检查点
./bin/memory-checkpoint create "完成任务X" -d "决策1" -t "待办1"

# 添加关键信息
./bin/memory-key-add "重要信息内容"

# 或使用完整路径
python3 memory_manager.py checkpoint --create "任务"
python3 memory_manager.py key --add "信息"
```

## 功能特性

### 1. 分层记忆系统
- **工作记忆**: 当前会话上下文
- **短期记忆**: `memory/cache.json` (50条)
- **长期记忆**: 每日归档到 `memory/YYYY-MM-DD.md`

### 2. 自动检查点
- 任务完成时自动创建
- 保留最近 10 个检查点
- 支持恢复到任意检查点状态

### 3. 关键信息标记
- 自动检测触发词: "记住这个", "这很重要", etc.
- 自动分类: #health, #preference, #task 等
- 同步到 Notion (可选)

## 文件结构

```
galatea-memory/
├── memory_manager.py      # 核心模块
├── SKILL.md               # 技能定义
├── README.md              # 本文档
└── bin/
    ├── memory-checkpoint  # 检查点 CLI
    └── memory-key-add     # 关键信息 CLI
```

## 工作目录结构

```
workspace/
├── memory/
│   ├── cache.json         # 短期记忆
│   ├── key_facts.md       # 关键信息
│   └── 2026-02-05.md      # 每日归档
└── checkpoints/
    ├── checkpoint_2026-02-05_14-30.json
    └── ...
```

## API 使用

```python
from memory_manager import MemoryManager, Priority

mm = MemoryManager()

# 短期记忆
mm.add_to_short_term("信息")
memories = mm.get_short_term_memories()

# 检查点
mm.create_checkpoint("任务", decisions=["决策"])

# 关键信息
mm.mark_key_info("重要内容", tags=["#health"])
```

## 与现有系统集成

- **elite-longterm-memory**: cache.json 作为 HOT RAM 层
- **Notion**: 关键信息自动备份
- **AGENTS.md**: 添加会话开始/结束时的读取/保存逻辑

## 测试

```bash
# 运行功能测试
cd /root/.openclaw/workspace/skills/galatea-memory
python3 -c "
from memory_manager import MemoryManager
mm = MemoryManager()

# 测试短期记忆
mm.add_to_short_term('测试内容')
print('短期记忆:', mm.get_short_term_memories())

# 测试检查点
cp_id = mm.create_checkpoint('测试任务')
print('检查点:', cp_id)

# 测试关键信息
entry_id = mm.mark_key_info('测试关键信息')
print('关键信息:', entry_id)

# 统计
print('统计:', mm.get_stats())
"
```

## 配置

环境变量:
- `GALATEA_WORKSPACE`: 工作目录路径 (默认: /root/.openclaw/workspace)

## 注意事项

1. cache.json 限制 50 条，超出自动归档
2. checkpoints 保留 10 个，超出自动清理
3. key_facts.md 使用 Markdown 格式便于阅读
4. Notion 同步需要配置 API key
