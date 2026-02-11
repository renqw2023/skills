#!/usr/bin/env python3
"""
Galatea Memory Manager - 分层记忆管理系统
============================================
实现三项核心功能：
1. 分层记忆系统 (Hierarchical Memory)
2. 自动检查点 (Auto-Checkpoint)  
3. 关键信息标记 (Key Info Marking)

Author: Galatea
Version: 1.0.0
"""

import os
import sys
import json
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('memory_manager')


class MemoryTier(Enum):
    """记忆层级"""
    WORKING = "working"      # 工作记忆 - 当前会话
    SHORT_TERM = "short"     # 短期记忆 - cache.json
    LONG_TERM = "long"       # 长期记忆 - 文件/Notion


class Priority(Enum):
    """信息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    timestamp: str
    tier: str
    priority: str
    tags: List[str]
    source: str
    category: str
    metadata: Dict[str, Any]
    
    @classmethod
    def create(cls, content: str, tier: MemoryTier = MemoryTier.SHORT_TERM,
               priority: Priority = Priority.NORMAL, tags: List[str] = None,
               source: str = "agent", category: str = "general",
               metadata: Dict[str, Any] = None) -> "MemoryEntry":
        """创建新记忆条目"""
        entry_id = hashlib.md5(
            f"{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        return cls(
            id=entry_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            tier=tier.value,
            priority=priority.name,
            tags=tags or [],
            source=source,
            category=category,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        return cls(**data)


@dataclass
class Checkpoint:
    """检查点"""
    id: str
    timestamp: str
    task: str
    decisions: List[str]
    todos: List[str]
    context: Dict[str, Any]
    
    @classmethod
    def create(cls, task: str, decisions: List[str] = None, 
               todos: List[str] = None, context: Dict[str, Any] = None) -> "Checkpoint":
        """创建新检查点"""
        now = datetime.now()
        checkpoint_id = now.strftime("checkpoint_%Y-%m-%d_%H-%M")
        
        return cls(
            id=checkpoint_id,
            timestamp=now.isoformat(),
            task=task,
            decisions=decisions or [],
            todos=todos or [],
            context=context or {}
        )
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Checkpoint":
        return cls(**data)


class MemoryManager:
    """记忆管理器主类"""
    
    # 触发词配置
    KEY_TRIGGERS = [
        r"记住这个",
        r"这很重要", 
        r"以后要记住",
        r"记一下",
        r"别忘了",
        r"重要"
    ]
    
    # 分类关键词
    CATEGORY_KEYWORDS = {
        "health": ["病", "痛", "医生", "药", "过敏", "症状", "健康"],
        "preference": ["喜欢", "讨厌", "偏好", "想要", "不想", "习惯"],
        "task": ["任务", "todo", "待办", "完成", "截止", "期限"],
        "contact": ["电话", "邮箱", "地址", "联系", "名字"],
        "project": ["项目", "开发", "代码", "架构", "设计"],
        "decision": ["决定", "选择", "采用", "使用", "放弃"]
    }
    
    def __init__(self, workspace_path: str = None):
        """初始化记忆管理器"""
        self.workspace = Path(workspace_path or os.environ.get(
            'GALATEA_WORKSPACE', '/root/.openclaw/workspace'
        ))
        
        # 目录结构
        self.memory_dir = self.workspace / "memory"
        self.checkpoint_dir = self.workspace / "checkpoints"
        self.cache_file = self.memory_dir / "cache.json"
        self.key_facts_file = self.memory_dir / "key_facts.md"
        
        # 配置
        self.max_cache_entries = 50
        self.max_checkpoints = 10
        
        # 初始化
        self._init_directories()
        self.cache = self._load_cache()
        
    def _init_directories(self):
        """初始化目录结构"""
        self.memory_dir.mkdir(exist_ok=True)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
    def _load_cache(self) -> List[Dict]:
        """加载短期记忆缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载缓存失败: {e}")
                return []
        return []
    
    def _save_cache(self):
        """保存短期记忆缓存"""
        try:
            # 限制条目数量
            if len(self.cache) > self.max_cache_entries:
                # 归档旧条目到长期记忆
                self._archive_old_cache_entries()
                self.cache = self.cache[-self.max_cache_entries:]
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def _archive_old_cache_entries(self):
        """将旧缓存条目归档到长期记忆"""
        old_entries = self.cache[:-self.max_cache_entries]
        if not old_entries:
            return
            
        # 归档到每日记忆文件
        today = datetime.now().strftime("%Y-%m-%d")
        archive_file = self.memory_dir / f"{today}.md"
        
        try:
            with open(archive_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n## [自动归档] 缓存条目 - {datetime.now().strftime('%H:%M')}\n")
                for entry in old_entries:
                    f.write(f"- {entry.get('content', '')}\n")
            logger.info(f"已归档 {len(old_entries)} 条缓存条目到 {archive_file}")
        except Exception as e:
            logger.error(f"归档缓存失败: {e}")
    
    # ==================== 功能 1: 分层记忆系统 ====================
    
    def add_to_short_term(self, content: str, priority: Priority = Priority.NORMAL,
                          tags: List[str] = None, category: str = "general") -> str:
        """添加条目到短期记忆"""
        entry = MemoryEntry.create(
            content=content,
            tier=MemoryTier.SHORT_TERM,
            priority=priority,
            tags=tags or [],
            category=category
        )
        
        self.cache.append(entry.to_dict())
        self._save_cache()
        
        logger.info(f"已添加到短期记忆: {entry.id}")
        return entry.id
    
    def get_short_term_memories(self, limit: int = 10) -> List[Dict]:
        """获取最近的短期记忆"""
        return self.cache[-limit:][::-1]
    
    def search_short_term(self, query: str) -> List[Dict]:
        """在短期记忆中搜索"""
        results = []
        query_lower = query.lower()
        
        for entry in self.cache:
            content = entry.get('content', '').lower()
            tags = [t.lower() for t in entry.get('tags', [])]
            
            if query_lower in content or any(query_lower in t for t in tags):
                results.append(entry)
        
        return results[::-1]  # 最新的在前
    
    def clear_short_term(self):
        """清空短期记忆"""
        # 先归档
        if self.cache:
            self._archive_old_cache_entries()
        self.cache = []
        self._save_cache()
        logger.info("短期记忆已清空")
    
    # ==================== 功能 2: 自动检查点 ====================
    
    def create_checkpoint(self, task: str, decisions: List[str] = None,
                          todos: List[str] = None, context: Dict = None) -> str:
        """创建检查点"""
        checkpoint = Checkpoint.create(
            task=task,
            decisions=decisions or [],
            todos=todos or [],
            context=context or {}
        )
        
        checkpoint_path = self.checkpoint_dir / f"{checkpoint.id}.json"
        
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
            
            # 清理旧检查点
            self._cleanup_old_checkpoints()
            
            logger.info(f"检查点已创建: {checkpoint.id}")
            return checkpoint.id
            
        except Exception as e:
            logger.error(f"创建检查点失败: {e}")
            return None
    
    def _cleanup_old_checkpoints(self):
        """清理旧检查点，保留最近 N 个"""
        try:
            checkpoints = sorted(
                self.checkpoint_dir.glob("checkpoint_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for old_checkpoint in checkpoints[self.max_checkpoints:]:
                old_checkpoint.unlink()
                logger.info(f"已删除旧检查点: {old_checkpoint.name}")
                
        except Exception as e:
            logger.error(f"清理检查点失败: {e}")
    
    def list_checkpoints(self) -> List[Dict]:
        """列出所有检查点"""
        checkpoints = []
        
        try:
            for checkpoint_path in sorted(
                self.checkpoint_dir.glob("checkpoint_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            ):
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    checkpoints.append({
                        'id': data.get('id'),
                        'timestamp': data.get('timestamp'),
                        'task': data.get('task'),
                        'file': checkpoint_path.name
                    })
        except Exception as e:
            logger.error(f"列出检查点失败: {e}")
        
        return checkpoints
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载指定检查点"""
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_path.exists():
            logger.warning(f"检查点不存在: {checkpoint_id}")
            return None
        
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Checkpoint.from_dict(data)
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None
    
    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """恢复到指定检查点状态"""
        checkpoint = self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return False
        
        try:
            # 恢复到短期记忆
            self.cache = checkpoint.context.get('cache', [])
            self._save_cache()
            
            logger.info(f"已恢复到检查点: {checkpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"恢复检查点失败: {e}")
            return False
    
    # ==================== 功能 3: 关键信息标记 ====================
    
    def detect_key_triggers(self, text: str) -> Tuple[bool, str]:
        """检测关键信息触发词"""
        for trigger in self.KEY_TRIGGERS:
            if re.search(trigger, text):
                # 提取触发词后的内容
                match = re.search(trigger + r"[,:：,\s]*(.+)", text)
                if match:
                    return True, match.group(1).strip()
                return True, text
        return False, ""
    
    def auto_classify(self, content: str) -> Tuple[str, List[str]]:
        """自动分类内容"""
        content_lower = content.lower()
        tags = []
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    tags.append(f"#{category}")
                    break
        
        # 确定主要类别
        category = "general"
        if tags:
            category = tags[0].replace('#', '')
        
        return category, tags
    
    def mark_key_info(self, content: str, source: str = "Master",
                      manual_tags: List[str] = None) -> str:
        """标记关键信息"""
        # 自动分类
        category, auto_tags = self.auto_classify(content)
        tags = list(set(auto_tags + (manual_tags or [])))
        
        # 创建条目
        entry = MemoryEntry.create(
            content=content,
            tier=MemoryTier.LONG_TERM,
            priority=Priority.HIGH,
            tags=tags,
            source=source,
            category=category
        )
        
        # 写入 key_facts.md
        self._write_key_fact(entry)
        
        # 同步到 Notion (可选)
        self._sync_to_notion(entry)
        
        logger.info(f"关键信息已标记: {entry.id}")
        return entry.id
    
    def _write_key_fact(self, entry: MemoryEntry):
        """写入关键信息到文件"""
        timestamp = datetime.fromisoformat(entry.timestamp)
        
        fact_text = f"""
## {timestamp.strftime('%Y-%m-%d %H:%M')}
**标签**: {' '.join(entry.tags)}
**来源**: {entry.source}
**内容**: {entry.content}

---
"""
        
        try:
            # 如果文件不存在，创建表头
            if not self.key_facts_file.exists():
                with open(self.key_facts_file, 'w', encoding='utf-8') as f:
                    f.write("# 关键信息记录 (Key Facts)\n\n")
                    f.write("此文件记录所有标记为 HIGH_PRIORITY 的重要信息。\n\n")
            
            # 追加新条目
            with open(self.key_facts_file, 'a', encoding='utf-8') as f:
                f.write(fact_text)
                
        except Exception as e:
            logger.error(f"写入关键信息失败: {e}")
    
    def _sync_to_notion(self, entry: MemoryEntry):
        """同步关键信息到 Notion"""
        # 这里可以调用 Notion API
        # 暂时记录日志，实际实现需要 Notion 集成
        logger.info(f"[Notion 同步] 条目 {entry.id} 待同步")
    
    def get_key_facts(self, category: str = None, limit: int = 20) -> List[Dict]:
        """获取关键信息列表"""
        if not self.key_facts_file.exists():
            return []
        
        try:
            with open(self.key_facts_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 markdown 格式
            facts = []
            sections = re.split(r'\n## ', content)
            
            for section in sections[1:]:  # 跳过表头
                lines = section.strip().split('\n')
                if len(lines) >= 3:
                    timestamp = lines[0].strip()
                    tags_line = lines[1] if '**标签**' in lines[1] else ''
                    source_line = lines[2] if '**来源**' in lines[2] else ''
                    content_line = lines[3] if '**内容**' in lines[3] else ''
                    
                    # 提取标签
                    tags = re.findall(r'#\w+', tags_line)
                    category_match = re.search(r'#(\w+)', tags_line)
                    fact_category = category_match.group(1) if category_match else 'general'
                    
                    if category and fact_category != category:
                        continue
                    
                    facts.append({
                        'timestamp': timestamp,
                        'category': fact_category,
                        'tags': tags,
                        'source': re.search(r'\*\*来源\*\*:\s*(.+)', source_line).group(1) if re.search(r'\*\*来源\*\*:\s*(.+)', source_line) else 'unknown',
                        'content': re.search(r'\*\*内容\*\*:\s*(.+)', content_line).group(1) if re.search(r'\*\*内容\*\*:\s*(.+)', content_line) else ''
                    })
            
            return facts[:limit][::-1]  # 最新的在前
            
        except Exception as e:
            logger.error(f"读取关键信息失败: {e}")
            return []
    
    # ==================== 工具方法 ====================
    
    def get_stats(self) -> Dict:
        """获取记忆统计信息"""
        return {
            'short_term_count': len(self.cache),
            'max_short_term': self.max_cache_entries,
            'checkpoint_count': len(list(self.checkpoint_dir.glob("checkpoint_*.json"))),
            'max_checkpoints': self.max_checkpoints,
            'key_facts_exists': self.key_facts_file.exists()
        }
    
    def auto_checkpoint_on_task_complete(self, task: str):
        """任务完成时自动创建检查点"""
        # 获取当前缓存作为上下文
        context = {'cache': self.cache}
        return self.create_checkpoint(
            task=task,
            context=context
        )


# ==================== CLI 接口 ====================

def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Galatea Memory Manager')
    parser.add_argument('--workspace', '-w', help='Workspace path')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # cache 命令
    cache_parser = subparsers.add_parser('cache', help='短期记忆管理')
    cache_parser.add_argument('--add', '-a', help='添加条目')
    cache_parser.add_argument('--list', '-l', action='store_true', help='列出条目')
    cache_parser.add_argument('--search', '-s', help='搜索条目')
    cache_parser.add_argument('--clear', action='store_true', help='清空缓存')
    cache_parser.add_argument('--limit', type=int, default=10, help='限制数量')
    
    # checkpoint 命令
    checkpoint_parser = subparsers.add_parser('checkpoint', help='检查点管理')
    checkpoint_parser.add_argument('--create', '-c', help='创建检查点 (任务描述)')
    checkpoint_parser.add_argument('--list', '-l', action='store_true', help='列出检查点')
    checkpoint_parser.add_argument('--load', help='加载检查点')
    checkpoint_parser.add_argument('--restore', help='恢复到检查点')
    checkpoint_parser.add_argument('--decisions', '-d', nargs='*', help='决策列表')
    checkpoint_parser.add_argument('--todos', '-t', nargs='*', help='待办列表')
    
    # key 命令
    key_parser = subparsers.add_parser('key', help='关键信息管理')
    key_parser.add_argument('--add', '-a', help='添加关键信息')
    key_parser.add_argument('--list', '-l', action='store_true', help='列出关键信息')
    key_parser.add_argument('--category', help='按类别筛选')
    key_parser.add_argument('--tags', nargs='*', help='标签列表')
    key_parser.add_argument('--source', default='Master', help='来源')
    
    # stats 命令
    subparsers.add_parser('stats', help='显示统计信息')
    
    args = parser.parse_args()
    
    # 初始化管理器
    mm = MemoryManager(args.workspace)
    
    if args.command == 'cache' or args.command is None:
        if args.add:
            entry_id = mm.add_to_short_term(args.add)
            print(f"✓ 已添加到短期记忆: {entry_id}")
        elif args.search:
            results = mm.search_short_term(args.search)
            print(f"找到 {len(results)} 条结果:")
            for r in results[:args.limit]:
                print(f"  [{r.get('timestamp', 'unknown')}] {r.get('content', '')[:50]}...")
        elif args.clear:
            mm.clear_short_term()
            print("✓ 短期记忆已清空")
        else:
            # 默认列出
            memories = mm.get_short_term_memories(args.limit)
            print(f"最近 {len(memories)} 条短期记忆:")
            for m in memories:
                print(f"  [{m.get('timestamp', 'unknown')[:16]}] {m.get('content', '')[:50]}...")
    
    elif args.command == 'checkpoint':
        if args.create:
            cp_id = mm.create_checkpoint(
                task=args.create,
                decisions=args.decisions,
                todos=args.todos
            )
            if cp_id:
                print(f"✓ 检查点已创建: {cp_id}")
            else:
                print("✗ 创建检查点失败")
        elif args.load:
            cp = mm.load_checkpoint(args.load)
            if cp:
                print(f"检查点: {cp.id}")
                print(f"时间: {cp.timestamp}")
                print(f"任务: {cp.task}")
                if cp.decisions:
                    print(f"决策: {', '.join(cp.decisions)}")
                if cp.todos:
                    print(f"待办: {', '.join(cp.todos)}")
            else:
                print(f"✗ 检查点不存在: {args.load}")
        elif args.restore:
            if mm.restore_checkpoint(args.restore):
                print(f"✓ 已恢复到检查点: {args.restore}")
            else:
                print(f"✗ 恢复失败: {args.restore}")
        else:
            # 默认列出
            checkpoints = mm.list_checkpoints()
            print(f"共 {len(checkpoints)} 个检查点 (最新在前):")
            for cp in checkpoints:
                print(f"  {cp['id']} - {cp['task'][:40]}...")
    
    elif args.command == 'key':
        if args.add:
            entry_id = mm.mark_key_info(
                content=args.add,
                source=args.source,
                manual_tags=args.tags
            )
            print(f"✓ 关键信息已标记: {entry_id}")
        else:
            # 默认列出
            facts = mm.get_key_facts(args.category)
            print(f"关键信息 ({len(facts)} 条):")
            for f in facts:
                print(f"  [{f['timestamp']}] [{f['category']}] {f['content'][:50]}...")
    
    elif args.command == 'stats':
        stats = mm.get_stats()
        print("记忆统计:")
        print(f"  短期记忆: {stats['short_term_count']}/{stats['max_short_term']}")
        print(f"  检查点: {stats['checkpoint_count']}/{stats['max_checkpoints']}")
        print(f"  关键信息文件: {'✓' if stats['key_facts_exists'] else '✗'}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
