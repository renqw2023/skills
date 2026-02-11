#!/usr/bin/env python3
"""
Galatea Memory Manager 集成示例
展示如何在 Agent 中使用记忆管理系统
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/skills/galatea-memory')

from memory_manager import MemoryManager, Priority

class GalateaMemoryIntegration:
    """Galatea 记忆集成类"""
    
    def __init__(self):
        self.mm = MemoryManager()
        self.session_start_time = None
        
    def on_session_start(self):
        """会话开始时调用"""
        from datetime import datetime
        self.session_start_time = datetime.now()
        
        # 1. 加载短期记忆
        memories = self.mm.get_short_term_memories(limit=10)
        
        # 2. 检查最近检查点
        checkpoints = self.mm.list_checkpoints()
        
        print("=" * 50)
        print("Galatea 记忆系统已加载")
        print(f"  恢复 {len(memories)} 条短期记忆")
        if checkpoints:
            print(f"  最近检查点: {checkpoints[0]['id']}")
        print("=" * 50)
        
        return {
            'memories': memories,
            'last_checkpoint': checkpoints[0] if checkpoints else None
        }
    
    def on_user_message(self, message: str) -> dict:
        """处理用户消息时调用"""
        result = {
            'is_key_info': False,
            'actions_taken': []
        }
        
        # 1. 检测关键信息触发词
        is_key, content = self.mm.detect_key_triggers(message)
        if is_key:
            entry_id = self.mm.mark_key_info(content)
            result['is_key_info'] = True
            result['actions_taken'].append(f"标记关键信息: {entry_id}")
            print(f"[记忆系统] 检测到关键信息，已标记")
        
        # 2. 保存到短期记忆
        self.mm.add_to_short_term(
            content=f"用户: {message}",
            priority=Priority.HIGH if is_key else Priority.NORMAL
        )
        
        return result
    
    def on_task_complete(self, task_description: str, decisions: list = None):
        """任务完成时调用"""
        cp_id = self.mm.auto_checkpoint_on_task_complete(task_description)
        print(f"[记忆系统] 任务完成，创建检查点: {cp_id}")
        return cp_id
    
    def on_session_end(self):
        """会话结束时调用"""
        # 创建最终检查点
        cp_id = self.mm.create_checkpoint(
            task="会话结束",
            context={'cache': self.mm.cache}
        )
        
        # 归档短期记忆
        # (超过 50 条的会自动归档)
        
        print(f"[记忆系统] 会话结束，最终检查点: {cp_id}")
        return cp_id
    
    def get_context_for_response(self) -> str:
        """获取用于生成响应的上下文"""
        memories = self.mm.get_short_term_memories(limit=5)
        key_facts = self.mm.get_key_facts(limit=3)
        
        context = []
        
        if key_facts:
            context.append("关键信息:")
            for f in key_facts:
                context.append(f"  - [{f['category']}] {f['content']}")
        
        if memories:
            context.append("\n近期记忆:")
            for m in memories[:3]:
                context.append(f"  - {m['content'][:50]}")
        
        return "\n".join(context) if context else ""


# 演示
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Galatea Memory Manager 集成演示")
    print("=" * 60 + "\n")
    
    integration = GalateaMemoryIntegration()
    
    # 1. 会话开始
    print(">> 1. 会话开始")
    context = integration.on_session_start()
    print()
    
    # 2. 处理用户消息
    print(">> 2. 处理用户消息")
    
    messages = [
        "你好，帮我查一下天气",
        "记住这个：我有前庭性偏头痛，避免高平衡动作",
        "今天的工作重点是完成代码审查",
        "这很重要，我明天下午有个会议"
    ]
    
    for msg in messages:
        result = integration.on_user_message(msg)
        status = "[关键]" if result['is_key_info'] else "[普通]"
        print(f"  {status} {msg[:40]}...")
    
    print()
    
    # 3. 任务完成
    print(">> 3. 任务完成")
    integration.on_task_complete(
        task_description="完成记忆系统演示",
        decisions=["集成演示通过", "准备部署"]
    )
    print()
    
    # 4. 获取上下文
    print(">> 4. 获取响应上下文")
    response_context = integration.get_context_for_response()
    print(response_context)
    print()
    
    # 5. 会话结束
    print(">> 5. 会话结束")
    integration.on_session_end()
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
