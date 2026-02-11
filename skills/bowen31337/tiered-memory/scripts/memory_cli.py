#!/usr/bin/env python3
"""
Tiered Memory CLI v2.0 - EvoClaw Architecture Implementation

Three-tier memory system with LLM-powered search, distillation, and consolidation.

Tiers:
  Hot (5KB):  Core memory — identity, owner profile, active context, critical lessons
  Warm (50KB): Scored recent facts with decay — 30-day retention
  Cold (∞):    Turso archive — unlimited, queryable, 10-year retention

Features:
  - LLM-powered tree search and distillation
  - Score-based tier placement (>=0.7 Hot, >=0.3 Warm, >=0.05 Cold, <0.05 Frozen)
  - Auto-pruning hot memory (max 20 lessons, 10 events, 10 tasks)
  - Multi-agent support (agent_id scoping)
  - Consolidation modes (quick/daily/monthly/full)
  - Metrics and observability

Usage:
  memory_cli.py store --text "..." --category "..." [--importance 0.7] [--agent-id default]
  memory_cli.py retrieve --query "..." [--llm] [--limit 5] [--agent-id default]
  memory_cli.py distill --text "conversation" [--llm] [--llm-endpoint http://...]
  memory_cli.py consolidate [--mode quick|daily|monthly|full] [--agent-id default]
  memory_cli.py sync-critical [--agent-id default]
  memory_cli.py metrics [--agent-id default]
  memory_cli.py hot --update key=value [--agent-id default]
  memory_cli.py tree [--show | --add PATH DESC | --remove PATH] [--agent-id default]
"""

import argparse
import json
import os
import sys
import time
import math
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path

# ─── Configuration ───

def load_config():
    """Load configuration from config.json with sensible defaults."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(os.path.dirname(script_dir), 'config.json')
    
    defaults = {
        'agent_id': 'default',
        'hot': {'max_bytes': 5120, 'max_lessons': 20, 'max_events': 10, 'max_tasks': 10},
        'warm': {'max_kb': 50, 'retention_days': 30, 'eviction_threshold': 0.3},
        'cold': {'backend': 'turso', 'retention_years': 10},
        'scoring': {'half_life_days': 30, 'reinforcement_boost': 0.1},
        'tree': {'max_nodes': 50, 'max_depth': 4, 'max_size_bytes': 2048},
        'distillation': {'aggression': 0.7, 'max_distilled_bytes': 100, 'mode': 'rule'},
        'consolidation': {'warm_eviction': 'hourly', 'tree_prune': 'daily', 'tree_rebuild': 'monthly'}
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
                # Merge with defaults
                for key in defaults:
                    if key not in config:
                        config[key] = defaults[key]
                    elif isinstance(defaults[key], dict):
                        for subkey in defaults[key]:
                            if subkey not in config[key]:
                                config[key][subkey] = defaults[key][subkey]
                return config
        except Exception as e:
            print(f"Warning: Failed to load config.json: {e}", file=sys.stderr)
    
    return defaults

CONFIG = load_config()

# Paths
WORKSPACE = os.environ.get("WORKSPACE", os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
MEMORY_DIR = os.path.join(WORKSPACE, "memory")

def get_agent_paths(agent_id='default'):
    """Get file paths for a specific agent."""
    agent_dir = os.path.join(MEMORY_DIR, agent_id) if agent_id != 'default' else MEMORY_DIR
    return {
        'warm_file': os.path.join(agent_dir, 'warm-memory.json'),
        'tree_file': os.path.join(agent_dir, 'memory-tree.json'),
        'hot_state_file': os.path.join(agent_dir, 'hot-memory-state.json'),
        'memory_md': os.path.join(WORKSPACE, f'MEMORY-{agent_id}.md' if agent_id != 'default' else 'MEMORY.md'),
        'metrics_file': os.path.join(agent_dir, 'metrics.json'),
        'agent_dir': agent_dir
    }

# ─── Scoring ───

def recency_decay(age_days, half_life=None):
    """Exponential decay: score halves every half_life days."""
    if half_life is None:
        half_life = CONFIG['scoring']['half_life_days']
    return math.exp(-age_days / half_life)

def reinforcement_factor(access_count, boost=None):
    """Reinforcement learning: accessed memories get boosted."""
    if boost is None:
        boost = CONFIG['scoring']['reinforcement_boost']
    return 1.0 + boost * access_count

def calculate_score(importance, created_at, access_count=0):
    """Calculate relevance score: importance × recency × reinforcement."""
    age_days = (time.time() - created_at) / 86400
    decay = recency_decay(age_days)
    reinf = reinforcement_factor(access_count)
    return importance * decay * reinf

def classify_tier(score):
    """Classify score into tier: hot/warm/cold/frozen."""
    if score >= 0.7:
        return 'hot'
    elif score >= 0.3:
        return 'warm'
    elif score >= 0.05:
        return 'cold'
    else:
        return 'frozen'

# ─── Tree Index ───

class MemoryTree:
    """Hierarchical memory index with constraints."""
    
    def __init__(self, tree_file):
        self.tree_file = tree_file
        self.nodes = {}
        self.max_nodes = CONFIG['tree']['max_nodes']
        self.max_depth = CONFIG['tree']['max_depth']
        self.max_size = CONFIG['tree']['max_size_bytes']
        self.load()
    
    def load(self):
        if os.path.exists(self.tree_file):
            with open(self.tree_file) as f:
                self.nodes = json.load(f)
        else:
            self.nodes = {
                'root': {'desc': 'Memory root', 'warm_count': 0, 'cold_count': 0, 
                        'last_access': 0, 'children': []}
            }
    
    def save(self):
        os.makedirs(os.path.dirname(self.tree_file), exist_ok=True)
        
        # Enforce size limit
        serialized = json.dumps(self.nodes)
        if len(serialized) > self.max_size:
            print(f"Warning: Tree size {len(serialized)} exceeds {self.max_size}, pruning...", 
                  file=sys.stderr)
            self._prune_to_fit()
        
        with open(self.tree_file, 'w') as f:
            json.dump(self.nodes, f, indent=2)
    
    def _prune_to_fit(self):
        """Remove least important nodes to fit size limit."""
        # Score nodes by: warm_count + cold_count + recency
        scored = []
        for path, node in self.nodes.items():
            if path == 'root':
                continue
            score = node.get('warm_count', 0) + node.get('cold_count', 0) * 0.1
            if node.get('last_access', 0) > 0:
                age_days = (time.time() - node['last_access']) / 86400
                score *= recency_decay(age_days, half_life=7)
            scored.append((path, score))
        
        scored.sort(key=lambda x: x[1])
        
        # Remove lowest scored until size fits
        while len(json.dumps(self.nodes)) > self.max_size and scored:
            path_to_remove, _ = scored.pop(0)
            self._remove_node_internal(path_to_remove)
    
    def add_node(self, path, desc):
        """Add a category node to the tree."""
        if len(self.nodes) >= self.max_nodes:
            return False
        
        depth = path.count('/') + 1
        if depth > self.max_depth:
            return False
        
        # Ensure parent exists
        if '/' in path:
            parent_path = path.rsplit('/', 1)[0]
            if parent_path not in self.nodes:
                parent_desc = parent_path.split('/')[-1].replace('_', ' ').title()
                self.add_node(parent_path, parent_desc)
        
        parent_path = path.rsplit('/', 1)[0] if '/' in path else 'root'
        
        if path not in self.nodes:
            self.nodes[path] = {
                'desc': desc[:100],  # Max 100 chars
                'warm_count': 0,
                'cold_count': 0,
                'last_access': 0,
                'children': []
            }
            if parent_path in self.nodes:
                if path not in self.nodes[parent_path].get('children', []):
                    self.nodes[parent_path].setdefault('children', []).append(path)
        
        self.save()
        return True
    
    def remove_node(self, path):
        """Remove a node if it has no data."""
        if path not in self.nodes or path == 'root':
            return False
        
        node = self.nodes[path]
        if node.get('warm_count', 0) > 0 or node.get('cold_count', 0) > 0:
            return False
        
        self._remove_node_internal(path)
        self.save()
        return True
    
    def _remove_node_internal(self, path):
        """Internal removal without save."""
        if path not in self.nodes:
            return
        
        # Remove from parent's children
        parent_path = path.rsplit('/', 1)[0] if '/' in path else 'root'
        if parent_path in self.nodes:
            children = self.nodes[parent_path].get('children', [])
            if path in children:
                children.remove(path)
        
        # Remove children recursively
        for child in list(self.nodes[path].get('children', [])):
            self._remove_node_internal(child)
        
        del self.nodes[path]
    
    def update_counts(self, path, warm_delta=0, cold_delta=0):
        """Update memory counts for a node."""
        if path in self.nodes:
            self.nodes[path]['warm_count'] = max(0, self.nodes[path].get('warm_count', 0) + warm_delta)
            self.nodes[path]['cold_count'] = max(0, self.nodes[path].get('cold_count', 0) + cold_delta)
            self.nodes[path]['last_access'] = time.time()
            self.save()
    
    def prune_dead_nodes(self, max_age_days=60):
        """Remove nodes with no activity in max_age_days."""
        cutoff = time.time() - (max_age_days * 86400)
        to_remove = []
        
        for path, node in self.nodes.items():
            if path == 'root':
                continue
            
            has_data = node.get('warm_count', 0) > 0 or node.get('cold_count', 0) > 0
            last_access = node.get('last_access', 0)
            is_old = last_access < cutoff
            
            if not has_data and (last_access == 0 or is_old):
                to_remove.append(path)
        
        for path in to_remove:
            self._remove_node_internal(path)
        
        if to_remove:
            self.save()
        
        return len(to_remove)
    
    def show(self):
        """Pretty-print the tree."""
        lines = ["Memory Tree Index", "=" * 50]
        
        def _show(path, indent=0):
            node = self.nodes.get(path, {})
            prefix = "  " * indent
            warm = node.get('warm_count', 0)
            cold = node.get('cold_count', 0)
            desc = node.get('desc', '')
            
            if path == 'root':
                lines.append(f"{prefix}📂 Root (warm:{warm}, cold:{cold})")
            else:
                lines.append(f"{prefix}📁 {path} — {desc}")
                lines.append(f"{prefix}   Memories: warm={warm}, cold={cold}")
            
            for child in sorted(node.get('children', [])):
                _show(child, indent + 1)
        
        _show('root')
        lines.append("")
        lines.append(f"Nodes: {len(self.nodes)}/{self.max_nodes}")
        lines.append(f"Size: {len(json.dumps(self.nodes))} / {self.max_size} bytes")
        return "\n".join(lines)

# ─── Hot Memory (Structured) ───

class HotMemory:
    """Structured core memory with auto-pruning."""
    
    def __init__(self, state_file):
        self.state_file = state_file
        self.max_bytes = CONFIG['hot']['max_bytes']
        self.max_lessons = CONFIG['hot']['max_lessons']
        self.max_events = CONFIG['hot']['max_events']
        self.max_tasks = CONFIG['hot']['max_tasks']
        self.state = {}
        self.load()
    
    def load(self):
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                self.state = json.load(f)
        else:
            self.state = {
                'identity': {},
                'owner_profile': {},
                'active_context': {'projects': [], 'events': [], 'tasks': []},
                'critical_lessons': []
            }
    
    def save(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self._enforce_limits()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _enforce_limits(self):
        """Auto-prune to stay within limits."""
        # Prune lessons (keep highest importance)
        lessons = self.state.get('critical_lessons', [])
        if isinstance(lessons, list) and len(lessons) > 0:
            # If lessons are dicts with importance
            if isinstance(lessons[0], dict):
                lessons.sort(key=lambda x: x.get('importance', 0.5), reverse=True)
                self.state['critical_lessons'] = lessons[:self.max_lessons]
            else:
                # Plain strings, just truncate
                self.state['critical_lessons'] = lessons[-self.max_lessons:]
        
        # Prune events (keep most recent)
        context = self.state.get('active_context', {})
        if 'events' in context:
            context['events'] = context['events'][-self.max_events:]
        
        # Prune tasks (keep most recent)
        if 'tasks' in context:
            context['tasks'] = context['tasks'][-self.max_tasks:]
        
        # Enforce total size
        serialized = json.dumps(self.state)
        while len(serialized) > self.max_bytes and self.state.get('critical_lessons'):
            # Remove oldest lesson
            self.state['critical_lessons'].pop(0)
            serialized = json.dumps(self.state)
    
    def update(self, key, data):
        """Update a section of hot memory."""
        if key == 'identity':
            self.state.setdefault('identity', {}).update(data)
        elif key == 'owner_profile':
            self.state.setdefault('owner_profile', {}).update(data)
        elif key == 'lesson':
            lessons = self.state.setdefault('critical_lessons', [])
            lesson = {
                'text': data.get('text', ''),
                'category': data.get('category', 'general'),
                'importance': data.get('importance', 0.7),
                'timestamp': time.time()
            }
            lessons.append(lesson)
        elif key == 'event':
            events = self.state.setdefault('active_context', {}).setdefault('events', [])
            events.append({
                'text': data.get('text', ''),
                'timestamp': time.time()
            })
        elif key == 'task':
            tasks = self.state.setdefault('active_context', {}).setdefault('tasks', [])
            tasks.append({
                'text': data.get('text', ''),
                'status': data.get('status', 'pending'),
                'timestamp': time.time()
            })
        elif key == 'project':
            projects = self.state.setdefault('active_context', {}).setdefault('projects', [])
            name = data.get('name', '')
            # Update existing or add new
            existing = [p for p in projects if p.get('name') == name]
            if existing:
                existing[0].update(data)
            else:
                projects.append(data)
        
        self.save()
    
    def generate_memory_md(self):
        """Generate MEMORY.md from hot state."""
        lines = [
            "# MEMORY.md - Long-Term Context",
            "",
            "*Core memory - auto-generated from tiered memory system*",
            "",
            "---",
            ""
        ]
        
        # Identity
        identity = self.state.get('identity', {})
        if identity:
            lines.append("## 🤖 Agent Identity")
            lines.append("")
            for k, v in identity.items():
                lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
            lines.append("")
        
        # Owner Profile
        owner = self.state.get('owner_profile', {})
        if owner:
            lines.append("## 👤 Owner Profile")
            lines.append("")
            for k, v in owner.items():
                if isinstance(v, list):
                    lines.append(f"- **{k.replace('_', ' ').title()}:** {', '.join(str(x) for x in v)}")
                else:
                    lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
            lines.append("")
        
        # Active Context
        context = self.state.get('active_context', {})
        
        if context.get('projects'):
            lines.append("## 💼 Active Projects")
            lines.append("")
            for p in context['projects']:
                lines.append(f"### {p.get('name', 'Unnamed')}")
                if p.get('description'):
                    lines.append(p['description'])
                if p.get('status'):
                    lines.append(f"**Status:** {p['status']}")
                lines.append("")
        
        if context.get('tasks'):
            lines.append("## ✅ Pending Tasks")
            lines.append("")
            for task in context['tasks'][-10:]:
                status = task.get('status', 'pending')
                text = task.get('text', '')
                lines.append(f"- [{status.upper()}] {text}")
            lines.append("")
        
        if context.get('events'):
            lines.append("## 📅 Recent Events")
            lines.append("")
            for event in context['events'][-10:]:
                ts = event.get('timestamp', 0)
                date = datetime.fromtimestamp(ts).strftime('%b %d') if ts else ''
                text = event.get('text', '')
                lines.append(f"- [{date}] {text}")
            lines.append("")
        
        # Critical Lessons
        lessons = self.state.get('critical_lessons', [])
        if lessons:
            lines.append("## 🎯 Critical Lessons")
            lines.append("")
            for lesson in lessons[-20:]:
                if isinstance(lesson, dict):
                    text = lesson.get('text', '')
                    cat = lesson.get('category', '')
                    if cat:
                        lines.append(f"- **[{cat}]** {text}")
                    else:
                        lines.append(f"- {text}")
                else:
                    lines.append(f"- {lesson}")
            lines.append("")
        
        lines.append("---")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        content = "\n".join(lines)
        
        # Final size check
        if len(content.encode()) > self.max_bytes:
            print(f"Warning: Generated MEMORY.md ({len(content.encode())} bytes) exceeds {self.max_bytes}", 
                  file=sys.stderr)
        
        return content

# ─── Warm Memory ───

class WarmMemory:
    """Scored recent facts with auto-eviction."""
    
    def __init__(self, warm_file):
        self.warm_file = warm_file
        self.facts = []
        self.max_kb = CONFIG['warm']['max_kb']
        self.max_bytes = self.max_kb * 1024
        self.retention_days = CONFIG['warm']['retention_days']
        self.threshold = CONFIG['warm']['eviction_threshold']
        self.load()
    
    def load(self):
        if os.path.exists(self.warm_file):
            with open(self.warm_file) as f:
                self.facts = json.load(f)
        else:
            self.facts = []
    
    def save(self):
        os.makedirs(os.path.dirname(self.warm_file), exist_ok=True)
        with open(self.warm_file, 'w') as f:
            json.dump(self.facts, f, indent=2)
    
    def add(self, text, category, importance=0.5):
        """Add a fact to warm memory."""
        fact_id = hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:12]
        fact = {
            'id': fact_id,
            'text': text,
            'category': category,
            'importance': importance,
            'created_at': time.time(),
            'access_count': 0,
            'score': importance
        }
        self.facts.append(fact)
        self._recalculate_scores()
        self._enforce_limits()
        self.save()
        return fact_id
    
    def _recalculate_scores(self):
        """Recalculate all scores."""
        for fact in self.facts:
            fact['score'] = calculate_score(
                fact['importance'],
                fact['created_at'],
                fact.get('access_count', 0)
            )
            fact['tier'] = classify_tier(fact['score'])
    
    def _enforce_limits(self):
        """Evict lowest-scored facts if over size limit."""
        self._recalculate_scores()
        
        while self._size() > self.max_bytes and len(self.facts) > 1:
            self.facts.sort(key=lambda x: x['score'])
            self.facts.pop(0)
    
    def _size(self):
        return len(json.dumps(self.facts).encode())
    
    def evict_expired(self):
        """Remove expired facts. Returns evicted."""
        cutoff = time.time() - (self.retention_days * 86400)
        
        keep = []
        evicted = []
        
        self._recalculate_scores()
        
        for fact in self.facts:
            score = fact['score']
            age = time.time() - fact['created_at']
            
            # Evict if: old AND low score
            if fact['created_at'] < cutoff and score < self.threshold:
                evicted.append(fact)
            else:
                keep.append(fact)
        
        self.facts = keep
        self.save()
        return evicted
    
    def search(self, query, limit=5):
        """Search warm facts by keyword overlap."""
        query_words = set(query.lower().split())
        results = []
        
        self._recalculate_scores()
        
        for fact in self.facts:
            fact_words = set(fact['text'].lower().split())
            cat_words = set(re.split(r'[/_\-]', fact.get('category', '').lower()))
            all_words = fact_words | cat_words
            overlap = len(query_words & all_words)
            
            if overlap > 0:
                relevance = (overlap / max(len(query_words), 1)) * fact['score']
                fact['access_count'] += 1
                results.append({**fact, 'relevance': relevance, 'tier': 'warm'})
        
        results.sort(key=lambda x: x['relevance'], reverse=True)
        self.save()
        return results[:limit]
    
    def get_by_category(self, category, limit=10):
        """Get facts by category prefix."""
        self._recalculate_scores()
        matches = [f for f in self.facts if f.get('category', '').startswith(category)]
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]

# ─── Cold Memory (Turso) ───

def normalize_db_url(db_url):
    """Convert libsql:// to https:// for HTTP API."""
    if db_url.startswith('libsql://'):
        return db_url.replace('libsql://', 'https://', 1)
    return db_url

def cold_store(fact_id, text, category, importance, agent_id, db_url, auth_token):
    """Store a fact in cold storage."""
    import urllib.request
    
    db_url = normalize_db_url(db_url)
    
    payload = {
        'requests': [
            {
                'type': 'execute',
                'stmt': {
                    'sql': """INSERT INTO cold_memories 
                             (id, agent_id, text, category, importance, created_at, access_count)
                             VALUES (?, ?, ?, ?, ?, ?, 0)""",
                    'args': [
                        {'type': 'text', 'value': fact_id},
                        {'type': 'text', 'value': agent_id},
                        {'type': 'text', 'value': text},
                        {'type': 'text', 'value': category},
                        {'type': 'float', 'value': importance},
                        {'type': 'integer', 'value': str(int(time.time()))}
                    ]
                }
            },
            {'type': 'close'}
        ]
    }
    
    try:
        req = urllib.request.Request(
            f"{db_url}/v2/pipeline",
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Cold store error: {e}", file=sys.stderr)
        return False

def cold_query(query, agent_id, limit, db_url, auth_token):
    """Query cold storage by keyword."""
    import urllib.request
    
    db_url = normalize_db_url(db_url)
    
    words = query.split()[:3]
    conditions = ' OR '.join([f"text LIKE '%{w}%'" for w in words])
    
    payload = {
        'requests': [
            {
                'type': 'execute',
                'stmt': {
                    'sql': f"""SELECT id, text, category, importance, created_at 
                              FROM cold_memories 
                              WHERE agent_id = ? AND ({conditions})
                              ORDER BY importance DESC, created_at DESC 
                              LIMIT ?""",
                    'args': [
                        {'type': 'text', 'value': agent_id},
                        {'type': 'integer', 'value': str(limit)}
                    ]
                }
            },
            {'type': 'close'}
        ]
    }
    
    try:
        req = urllib.request.Request(
            f"{db_url}/v2/pipeline",
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            rows = data.get('results', [{}])[0].get('response', {}).get('result', {}).get('rows', [])
            results = []
            for row in rows:
                results.append({
                    'id': row[0]['value'],
                    'text': row[1]['value'],
                    'category': row[2]['value'],
                    'importance': float(row[3]['value']),
                    'created_at': int(row[4]['value']),
                    'tier': 'cold'
                })
            return results
    except Exception as e:
        print(f"Cold query error: {e}", file=sys.stderr)
        return []

def cold_sync_critical(agent_id, hot_state, tree_nodes, db_url, auth_token):
    """Critical sync: hot state + tree to cloud."""
    import urllib.request
    
    db_url = normalize_db_url(db_url)
    
    data = {
        'hot_state': hot_state,
        'tree_nodes': tree_nodes,
        'timestamp': time.time()
    }
    
    payload = {
        'requests': [
            {
                'type': 'execute',
                'stmt': {
                    'sql': """INSERT OR REPLACE INTO critical_state 
                             (agent_id, data, updated_at)
                             VALUES (?, ?, ?)""",
                    'args': [
                        {'type': 'text', 'value': agent_id},
                        {'type': 'text', 'value': json.dumps(data)},
                        {'type': 'integer', 'value': str(int(time.time()))}
                    ]
                }
            },
            {'type': 'close'}
        ]
    }
    
    try:
        req = urllib.request.Request(
            f"{db_url}/v2/pipeline",
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Critical sync error: {e}", file=sys.stderr)
        return False

def cold_init_tables(db_url, auth_token):
    """Initialize Turso tables."""
    import urllib.request
    
    db_url = normalize_db_url(db_url)
    
    payload = {
        'requests': [
            {
                'type': 'execute',
                'stmt': {
                    'sql': """CREATE TABLE IF NOT EXISTS cold_memories (
                        id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        text TEXT NOT NULL,
                        category TEXT NOT NULL,
                        importance REAL DEFAULT 0.5,
                        created_at INTEGER NOT NULL,
                        access_count INTEGER DEFAULT 0
                    )"""
                }
            },
            {
                'type': 'execute',
                'stmt': {'sql': "CREATE INDEX IF NOT EXISTS idx_cold_agent_category ON cold_memories(agent_id, category)"}
            },
            {
                'type': 'execute',
                'stmt': {'sql': "CREATE INDEX IF NOT EXISTS idx_cold_agent_created ON cold_memories(agent_id, created_at)"}
            },
            {
                'type': 'execute',
                'stmt': {
                    'sql': """CREATE TABLE IF NOT EXISTS critical_state (
                        agent_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        updated_at INTEGER NOT NULL
                    )"""
                }
            },
            {'type': 'close'}
        ]
    }
    
    try:
        req = urllib.request.Request(
            f"{db_url}/v2/pipeline",
            data=json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {auth_token}',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Table init error: {e}", file=sys.stderr)
        return False

# ─── Retrieval (Multi-tier with LLM) ───

def retrieve(query, agent_id='default', limit=5, use_llm=False, 
             llm_endpoint=None, db_url=None, auth_token=None):
    """
    Multi-tier retrieval: tree search → warm → cold.
    
    Args:
        query: Search query
        agent_id: Agent identifier
        limit: Max results
        use_llm: Use LLM-powered tree search
        llm_endpoint: HTTP endpoint for LLM
        db_url: Turso URL for cold storage
        auth_token: Turso auth token
    
    Returns:
        list: Retrieved memories with tier labels
    """
    paths = get_agent_paths(agent_id)
    tree = MemoryTree(paths['tree_file'])
    warm = WarmMemory(paths['warm_file'])
    
    results = []
    seen_ids = set()
    
    # 1. Tree search to find relevant categories
    if use_llm and llm_endpoint:
        # Use LLM tree search
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tree_search = os.path.join(script_dir, 'tree_search.py')
        
        try:
            cmd = [
                'python3', tree_search,
                '--query', query,
                '--tree-file', paths['tree_file'],
                '--mode', 'llm',
                '--llm-endpoint', llm_endpoint,
                '--top-k', str(3)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                tree_results = json.loads(result.stdout)
                relevant_paths = [r['path'] for r in tree_results.get('results', [])]
            else:
                # Fallback to keyword
                print("LLM tree search failed, using keyword", file=sys.stderr)
                relevant_paths = [r['path'] for r in tree.nodes.keys() if r != 'root'][:3]
        except Exception as e:
            print(f"Tree search error: {e}", file=sys.stderr)
            relevant_paths = []
    else:
        # Keyword-based tree search
        from tree_search import search_keyword
        tree_results = search_keyword(tree.nodes, query, top_k=3)
        relevant_paths = [r['path'] for r in tree_results]
    
    # 2. Search warm memory (targeted by categories)
    for path in relevant_paths:
        cat_facts = warm.get_by_category(path, limit=limit)
        for fact in cat_facts:
            if fact['id'] not in seen_ids:
                fact['tier'] = 'warm'
                results.append(fact)
                seen_ids.add(fact['id'])
    
    # General warm search
    warm_hits = warm.search(query, limit=limit)
    for fact in warm_hits:
        if fact['id'] not in seen_ids:
            results.append(fact)
            seen_ids.add(fact['id'])
    
    # 3. Cold search if needed
    if len(results) < limit and db_url and auth_token:
        cold_hits = cold_query(query, agent_id, limit - len(results), db_url, auth_token)
        for fact in cold_hits:
            if fact['id'] not in seen_ids:
                results.append(fact)
                seen_ids.add(fact['id'])
    
    # Sort by relevance/score
    results.sort(key=lambda x: x.get('relevance', x.get('score', x.get('importance', 0))), reverse=True)
    return results[:limit]

# ─── Consolidation ───

def consolidate(mode='quick', agent_id='default', db_url=None, auth_token=None):
    """
    Run consolidation based on mode.
    
    Modes:
        quick: Warm eviction + score recalc
        daily: quick + tree prune
        monthly: daily + tree rebuild + cold cleanup
        full: everything with full recalculation
    """
    paths = get_agent_paths(agent_id)
    tree = MemoryTree(paths['tree_file'])
    warm = WarmMemory(paths['warm_file'])
    hot = HotMemory(paths['hot_state_file'])
    
    stats = {
        'mode': mode,
        'agent_id': agent_id,
        'timestamp': datetime.now().isoformat()
    }
    
    # Quick: Warm eviction
    evicted = warm.evict_expired()
    stats['evicted_warm'] = len(evicted)
    
    # Archive to cold
    archived = 0
    if db_url and auth_token:
        for fact in evicted:
            if cold_store(
                fact['id'],
                fact['text'],
                fact.get('category', 'uncategorized'),
                fact.get('importance', 0.5),
                agent_id,
                db_url,
                auth_token
            ):
                archived += 1
                # Update tree cold count
                tree.update_counts(fact.get('category', 'uncategorized'), cold_delta=1)
    
    stats['archived_cold'] = archived
    
    # Daily: Tree prune
    if mode in ['daily', 'monthly', 'full']:
        pruned = tree.prune_dead_nodes(max_age_days=60)
        stats['pruned_nodes'] = pruned
    
    # Monthly: Tree rebuild (placeholder for LLM)
    if mode in ['monthly', 'full']:
        # TODO: LLM-powered tree rebuild
        # For now, just recalculate all counts
        for path in tree.nodes:
            if path == 'root':
                continue
            warm_facts = warm.get_by_category(path, limit=1000)
            tree.nodes[path]['warm_count'] = len(warm_facts)
        tree.save()
        stats['tree_rebuilt'] = True
    
    # Rebuild hot memory
    content = hot.generate_memory_md()
    with open(paths['memory_md'], 'w') as f:
        f.write(content)
    stats['hot_size_bytes'] = len(content.encode())
    
    # Update metrics
    update_metrics(agent_id, {
        'consolidation_count': 1,
        'last_consolidation': time.time(),
        'evictions_today': stats['evicted_warm']
    })
    
    return stats

# ─── Metrics ───

def load_metrics(agent_id='default'):
    """Load metrics for an agent."""
    paths = get_agent_paths(agent_id)
    if os.path.exists(paths['metrics_file']):
        with open(paths['metrics_file']) as f:
            return json.load(f)
    return {
        'retrieval_count': 0,
        'evictions_today': 0,
        'reinforcements_today': 0,
        'consolidation_count': 0,
        'last_consolidation': 0,
        'context_tokens_saved': 0
    }

def save_metrics(agent_id, metrics):
    """Save metrics for an agent."""
    paths = get_agent_paths(agent_id)
    os.makedirs(paths['agent_dir'], exist_ok=True)
    with open(paths['metrics_file'], 'w') as f:
        json.dump(metrics, f, indent=2)

def update_metrics(agent_id, updates):
    """Update specific metrics."""
    metrics = load_metrics(agent_id)
    for key, delta in updates.items():
        if key in metrics:
            if isinstance(metrics[key], (int, float)):
                metrics[key] += delta
            else:
                metrics[key] = delta
        else:
            metrics[key] = delta
    save_metrics(agent_id, metrics)

def get_metrics(agent_id='default'):
    """Get comprehensive metrics for an agent."""
    paths = get_agent_paths(agent_id)
    tree = MemoryTree(paths['tree_file'])
    warm = WarmMemory(paths['warm_file'])
    
    metrics = load_metrics(agent_id)
    
    # Calculate current stats
    tree_size = len(json.dumps(tree.nodes))
    warm_size = warm._size()
    
    if os.path.exists(paths['hot_state_file']):
        with open(paths['hot_state_file']) as f:
            hot_size = len(json.dumps(json.load(f)))
    else:
        hot_size = 0
    
    metrics.update({
        'tree_index_size_bytes': tree_size,
        'tree_node_count': len(tree.nodes),
        'hot_memory_size_bytes': hot_size,
        'warm_memory_count': len(warm.facts),
        'warm_memory_size_kb': round(warm_size / 1024, 1),
        'timestamp': datetime.now().isoformat()
    })
    
    return metrics

# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(
        description='Tiered Memory CLI v2.0 - EvoClaw Architecture',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    sub = parser.add_subparsers(dest='command')
    
    # Common args
    def add_common_args(p):
        p.add_argument('--agent-id', default='default', help='Agent identifier')
        p.add_argument('--db-url', help='Turso database URL')
        p.add_argument('--auth-token', help='Turso auth token')
    
    # store
    p_store = sub.add_parser('store', help='Store a fact in memory')
    p_store.add_argument('--text', required=True)
    p_store.add_argument('--category', required=True)
    p_store.add_argument('--importance', type=float, default=0.5)
    add_common_args(p_store)
    
    # retrieve
    p_ret = sub.add_parser('retrieve', help='Search across all tiers')
    p_ret.add_argument('--query', required=True)
    p_ret.add_argument('--limit', type=int, default=5)
    p_ret.add_argument('--llm', action='store_true', help='Use LLM-powered search')
    p_ret.add_argument('--llm-endpoint', help='LLM HTTP endpoint')
    add_common_args(p_ret)
    
    # distill
    p_dist = sub.add_parser('distill', help='Distill conversation to structured fact')
    p_dist.add_argument('--text', help='Raw conversation text')
    p_dist.add_argument('--file', help='Read from file')
    p_dist.add_argument('--llm', action='store_true', help='Use LLM distillation')
    p_dist.add_argument('--llm-endpoint', help='LLM HTTP endpoint')
    p_dist.add_argument('--core-summary', action='store_true', help='Generate core summary')
    
    # consolidate
    p_con = sub.add_parser('consolidate', help='Run consolidation')
    p_con.add_argument('--mode', choices=['quick', 'daily', 'monthly', 'full'], default='quick')
    add_common_args(p_con)
    
    # sync-critical
    p_sync = sub.add_parser('sync-critical', help='Sync hot+tree to cloud')
    add_common_args(p_sync)
    
    # metrics
    p_met = sub.add_parser('metrics', help='Show memory metrics')
    p_met.add_argument('--agent-id', default='default')
    
    # hot
    p_hot = sub.add_parser('hot', help='Manage hot memory')
    p_hot.add_argument('--update', nargs=2, metavar=('KEY', 'JSON'), help='Update hot state')
    p_hot.add_argument('--rebuild', action='store_true', help='Rebuild MEMORY.md')
    add_common_args(p_hot)
    
    # tree
    p_tree = sub.add_parser('tree', help='Manage tree index')
    p_tree.add_argument('--show', action='store_true')
    p_tree.add_argument('--add', nargs=2, metavar=('PATH', 'DESC'))
    p_tree.add_argument('--remove')
    p_tree.add_argument('--prune', action='store_true', help='Remove dead nodes')
    p_tree.add_argument('--agent-id', default='default')
    
    # cold
    p_cold = sub.add_parser('cold', help='Manage cold storage')
    p_cold.add_argument('--init', action='store_true', help='Initialize tables')
    p_cold.add_argument('--query')
    p_cold.add_argument('--limit', type=int, default=10)
    p_cold.add_argument('--agent-id', default='default')
    p_cold.add_argument('--db-url', required=True)
    p_cold.add_argument('--auth-token', required=True)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Commands
    if args.command == 'store':
        paths = get_agent_paths(args.agent_id)
        tree = MemoryTree(paths['tree_file'])
        warm = WarmMemory(paths['warm_file'])
        
        # Add to warm
        fact_id = warm.add(args.text, args.category, args.importance)
        
        # Update tree
        tree.add_node(args.category, args.category.split('/')[-1].replace('_', ' ').title())
        tree.update_counts(args.category, warm_delta=1)
        
        # Archive to cold if configured
        cold_synced = False
        if args.db_url and args.auth_token:
            cold_synced = cold_store(
                fact_id, args.text, args.category, args.importance,
                args.agent_id, args.db_url, args.auth_token
            )
            if cold_synced:
                tree.update_counts(args.category, cold_delta=1)
        
        print(json.dumps({
            'id': fact_id,
            'category': args.category,
            'tier': classify_tier(args.importance),
            'cold_synced': cold_synced
        }))
    
    elif args.command == 'retrieve':
        results = retrieve(
            args.query,
            agent_id=args.agent_id,
            limit=args.limit,
            use_llm=args.llm,
            llm_endpoint=args.llm_endpoint,
            db_url=args.db_url,
            auth_token=args.auth_token
        )
        
        update_metrics(args.agent_id, {'retrieval_count': 1})
        print(json.dumps(results, indent=2))
    
    elif args.command == 'distill':
        # Load distiller module
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, script_dir)
        import distiller
        
        if args.file:
            with open(args.file) as f:
                text = f.read()
        elif args.text:
            text = args.text
        else:
            parser.error('--text or --file required')
        
        if args.llm and args.llm_endpoint:
            result = distiller.distill_llm(text, args.llm_endpoint)
        else:
            result = distiller.distill_rule_based(text)
        
        output = {
            'distilled': result,
            'mode': 'llm' if args.llm else 'rule',
            'original_size': len(text),
            'distilled_size': len(json.dumps(result))
        }
        
        if args.core_summary:
            output['core_summary'] = distiller.generate_core_summary(result)
        
        print(json.dumps(output, indent=2))
    
    elif args.command == 'consolidate':
        stats = consolidate(
            mode=args.mode,
            agent_id=args.agent_id,
            db_url=args.db_url,
            auth_token=args.auth_token
        )
        print(json.dumps(stats, indent=2))
    
    elif args.command == 'sync-critical':
        paths = get_agent_paths(args.agent_id)
        
        with open(paths['hot_state_file']) as f:
            hot_state = json.load(f)
        
        with open(paths['tree_file']) as f:
            tree_nodes = json.load(f)
        
        if args.db_url and args.auth_token:
            ok = cold_sync_critical(
                args.agent_id,
                hot_state,
                tree_nodes,
                args.db_url,
                args.auth_token
            )
            print(json.dumps({'synced': ok, 'timestamp': datetime.now().isoformat()}))
        else:
            print(json.dumps({'error': 'db-url and auth-token required'}))
    
    elif args.command == 'metrics':
        metrics = get_metrics(args.agent_id)
        print(json.dumps(metrics, indent=2))
    
    elif args.command == 'hot':
        paths = get_agent_paths(args.agent_id)
        hot = HotMemory(paths['hot_state_file'])
        
        if args.update:
            key, data_json = args.update
            data = json.loads(data_json)
            hot.update(key, data)
            
            # Sync to cloud if configured
            if args.db_url and args.auth_token:
                cold_sync_critical(
                    args.agent_id,
                    hot.state,
                    {},
                    args.db_url,
                    args.auth_token
                )
            
            print(json.dumps({'updated': key}))
        
        elif args.rebuild:
            content = hot.generate_memory_md()
            with open(paths['memory_md'], 'w') as f:
                f.write(content)
            print(json.dumps({
                'output': paths['memory_md'],
                'size_bytes': len(content.encode()),
                'max_bytes': hot.max_bytes
            }))
        
        else:
            print(json.dumps(hot.state, indent=2))
    
    elif args.command == 'tree':
        paths = get_agent_paths(args.agent_id)
        tree = MemoryTree(paths['tree_file'])
        
        if args.show:
            print(tree.show())
        elif args.add:
            ok = tree.add_node(args.add[0], args.add[1])
            print(json.dumps({'path': args.add[0], 'added': ok}))
        elif args.remove:
            ok = tree.remove_node(args.remove)
            print(json.dumps({'path': args.remove, 'removed': ok}))
        elif args.prune:
            pruned = tree.prune_dead_nodes()
            print(json.dumps({'pruned': pruned}))
        else:
            print(tree.show())
    
    elif args.command == 'cold':
        if args.init:
            ok = cold_init_tables(args.db_url, args.auth_token)
            print(json.dumps({'initialized': ok}))
        elif args.query:
            results = cold_query(args.query, args.agent_id, args.limit, args.db_url, args.auth_token)
            print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
