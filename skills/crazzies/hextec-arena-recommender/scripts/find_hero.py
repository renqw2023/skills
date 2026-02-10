#!/usr/bin/env python3
"""
海克斯大乱斗推荐器 - 修复版
修复了查询顺序：hero-data.json 优先于 aliases.json
"""

import json
import sys

# 路径配置
SCRIPT_DIR = '/root/.openclaw/workspace/skills/hextec-arena-recommender/scripts'
DATA_DIR = '/root/.openclaw/workspace/skills/hextec-arena-recommender/references'

def load_data():
    """加载所有数据文件"""
    with open(f'{DATA_DIR}/hero-data.json', 'r', encoding='utf-8') as f:
        hero_data = json.load(f)
    
    with open(f'{DATA_DIR}/hero-aliases.json', 'r', encoding='utf-8') as f:
        aliases = json.load(f)
    
    with open(f'{SCRIPT_DIR}/hero_numbers.json', 'r', encoding='utf-8') as f:
        hero_numbers = json.load(f)
    
    return hero_data, aliases, hero_numbers

def find_hero_id(query, hero_data, aliases, hero_numbers):
    """
    查找英雄ID - 修复版
    查询顺序：
    1. hero_data 的 display_name (官方中文名)
    2. hero_data 的 name (英文名)
    3. hero_data 的 alias (别名)
    4. aliases 玩家别名表
    """
    query = query.strip().lower()
    
    print(f"查询: {query}", file=sys.stderr)
    
    # 1. 先查 hero_data (官方名称优先)
    print("  [Step 1] 查 hero-data.json...", file=sys.stderr)
    for hero_id, info in hero_data.items():
        if query == info.get('display_name', '').lower():
            print(f"    ✓ 匹配 display_name: {info['display_name']} -> {hero_id}", file=sys.stderr)
            return hero_id, info
        if query == info.get('name', '').lower():
            print(f"    ✓ 匹配 name: {info['name']} -> {hero_id}", file=sys.stderr)
            return hero_id, info
        if query == info.get('alias', '').lower():
            print(f"    ✓ 匹配 alias: {info['alias']} -> {hero_id}", file=sys.stderr)
            return hero_id, info
    
    # 2. 查 aliases (玩家别名)
    print("  [Step 2] 查 hero-aliases.json...", file=sys.stderr)
    if query in aliases:
        hero_id = aliases[query]
        print(f"    ✓ 匹配玩家别名: {query} -> {hero_id}", file=sys.stderr)
        if hero_id in hero_data:
            return hero_id, hero_data[hero_id]
        return hero_id, None
    
    # 3. 部分匹配 (用户输入包含在名称中)
    print("  [Step 3] 部分匹配...", file=sys.stderr)
    for hero_id, info in hero_data.items():
        for field in ['display_name', 'name', 'alias']:
            if query in info.get(field, '').lower():
                print(f"    ✓ {field}: {query} in {info[field]}", file=sys.stderr)
                return hero_id, info
    
    return None, None

def get_hero_number(hero_id, hero_numbers):
    """获取英雄编号"""
    return hero_numbers.get(hero_id)

def main():
    if len(sys.argv) < 2:
        print("用法: python find_hero.py <英雄名>", file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    
    hero_data, aliases, hero_numbers = load_data()
    hero_id, info = find_hero_id(query, hero_data, aliases, hero_numbers)
    
    if hero_id:
        number = get_hero_number(hero_id, hero_numbers)
        print(f"英雄: {info['display_name']} ({hero_id})")
        print(f"编号: {number}")
        print(f"URL: https://hextech.dtodo.cn/zh-CN/champion-stats/{number}")
    else:
        print(f"未找到: {query}")
        sys.exit(1)

if __name__ == "__main__":
    main()
