#!/usr/bin/env python3
"""海克斯大乱斗推荐器"""

import json, re, sys, os, subprocess

BASE_URL = "https://hextech.dtodo.cn"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

def load_json(fn):
    try:
        with open(os.path.join(SKILL_DIR, "references", fn), "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def fetch_html(hero_number):
    url = f"{BASE_URL}/zh-CN/champion-stats/{hero_number}"
    try:
        r = subprocess.run(["curl", "-s", "-L", "-A", "Mozilla/5.0", url], capture_output=True, text=True, timeout=30)
        return r.stdout
    except:
        return None

def find_hero(hero_name, aliases_data, hero_numbers_data):
    search = hero_name.lower().strip()
    for k, v in aliases_data.items():
        if k.lower() == search:
            english = v
            break
    else:
        english = None
    if english:
        if english in hero_numbers_data: return hero_numbers_data[english]
        if english.capitalize() in hero_numbers_data: return hero_numbers_data[english.capitalize()]
    for k, v in hero_numbers_data.items():
        if search in k.lower(): return v
    return None

def get_hero_name(html):
    # 从 title 标签提取
    title_match = re.search(r'<title>([^<]+)', html)
    if title_match:
        title = title_match.group(1)
        # 格式: "韦鲁斯海克斯强化推荐 - ..."
        hero = title.replace('海克斯强化推荐', '').replace('海克斯大乱斗', '').strip()
        return hero.split(' ')[0] if ' ' in hero else hero
    
    return "UnknownHero"

def get_tier(html):
    m = re.search(r'T([1-6])', html)
    return m.group(1) if m else "?"

def parse_items(html, items_data):
    """优先从"情景装备"区域获取装备"""
    # 先尝试从"情景装备"区域获取
    # 查找包含"情景装备"的区域
    situational_section = re.search(r'(?is)情景装备.*?(?=<h2|$)', html)
    
    if situational_section:
        # 从情景装备区域获取装备图标
        items, seen = [], set()
        for m in re.findall(r'<img[^>]*src="[^"]*item-icons/(\d+)\.png"', situational_section.group(0)):
            if m not in seen:
                seen.add(m)
                items.append(items_data.get(m, f"Item{m}"))
        if items:
            return items[:8]
    
    # 如果情景装备区域没有或没有装备，获取所有装备图标
    items, seen = [], set()
    for m in re.findall(r'<img[^>]*src="[^"]*item-icons/(\d+)\.png"', html):
        if m not in seen:
            seen.add(m)
            items.append(items_data.get(m, f"Item{m}"))
    return items[:12]

def parse_augments(html, augments_data):
    augs, seen = [], set()
    rarity_map = {"黄金": "Gold", "白银": "Silver", "棱彩": "Prismatic"}
    
    for row in re.findall(r'(<tr[^>]*>.*?</tr>)', html, re.DOTALL):
        m = re.search(r'>#(\d+)</span>', row)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        
        wr = re.search(r'>([\d.]+)%</span>', row)
        if not wr or float(wr.group(1)) <= 0:
            continue
        
        pr = re.search(r'>([\d.]+)%</td>', row)
        info = augments_data.get(m.group(1), {"name": f"AUG-{m.group(1)}", "rarity": "Unknown"})
        augs.append({
            "name": info.get("name", f"AUG-{m.group(1)}"),
            "rarity": rarity_map.get(info.get("rarity", "Unknown"), info.get("rarity", "Unknown")),
            "wr": wr.group(1) + "%",
            "pr": pr.group(1) + "%" if pr else "0%"
        })
    
    rarity_order = {"Prismatic": 0, "Gold": 1, "Silver": 2, "Unknown": 3}
    augs.sort(key=lambda x: (rarity_order.get(x["rarity"], 3), -float(x["wr"].replace("%", ""))))
    return augs

def output(hero, tier, items, augs, url):
    lines = []
    lines.append(f"[英雄] {hero} | 层级 T{tier}")
    lines.append(f"[装备] {', '.join(items[:8])}")    
    groups = {"Prismatic": [], "Gold": [], "Silver": []}
    for a in augs:
        if a["rarity"] in groups:
            groups[a["rarity"]].append(a)
    
    if groups["Prismatic"]:
        lines.append(f"[棱彩] " + " | ".join([f"{x['name'][:10]}({x['wr']})" for x in groups["Prismatic"][:5]]))
    if groups["Gold"]:
        lines.append(f"[黄金] " + " | ".join([f"{x['name'][:10]}({x['wr']})" for x in groups["Gold"][:5]]))
    if groups["Silver"]:
        lines.append(f"[白银] " + " | ".join([f"{x['name'][:10]}({x['wr']})" for x in groups["Silver"][:5]]))
    
    # 使用更清晰的链接格式
    lines.append(f"📊 数据来源: {url}")
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("用法: python fetch_recommender.py <英雄名>")
        sys.exit(1)
    
    hero = sys.argv[1]
    aliases = load_json("hero-aliases.json")
    hero_numbers = load_json("hero-numbers.json")
    augments = load_json("augments.json")
    items = load_json("items_mapping_new.json")
    
    hero_id = sys.argv[2] if len(sys.argv) >= 3 else find_hero(hero, aliases, hero_numbers)
    
    if not hero_id:
        print(f"未找到英雄: {hero}")
        sys.exit(1)
    
    html = fetch_html(hero_id)
    if not html:
        print("获取失败")
        sys.exit(1)
    
    print(output(get_hero_name(html), get_tier(html), parse_items(html, items), parse_augments(html, augments), f"{BASE_URL}/zh-CN/champion-stats/{hero_id}"))

main()
