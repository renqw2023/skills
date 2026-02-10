"""Interactive setup wizard for NIMA — fully automated OpenClaw integration."""
import sys
import os
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from ..config.auto import detect_openclaw, get_nima_config, setup_paths


def find_nima_core_root() -> Path:
    """Find the nima-core package root (contains package.json + hooks/)."""
    # Check common locations
    candidates = [
        Path(__file__).resolve().parent.parent.parent,  # nima_core/cli/setup.py → nima-core/
        Path.cwd(),
        Path.home() / ".openclaw" / "workspace" / "nima-core",
    ]
    
    # Also check if pip-installed — find the package location
    try:
        import nima_core
        pkg_dir = Path(nima_core.__file__).resolve().parent.parent
        candidates.insert(0, pkg_dir)
    except (ImportError, AttributeError):
        pass
    
    for candidate in candidates:
        if (candidate / "package.json").exists() and (candidate / "hooks").is_dir():
            return candidate
    
    # No valid root found — warn and return best guess
    import warnings
    warnings.warn(
        f"Could not find nima-core root with package.json + hooks/. "
        f"Checked: {[str(c) for c in candidates]}. "
        f"Hook installation may fail.",
        stacklevel=2,
    )
    return candidates[0]


def install_hooks(nima_root: Path) -> bool:
    """Install NIMA hooks into OpenClaw using `openclaw hooks install`."""
    print("\n🔗 Installing NIMA hooks into OpenClaw...")
    
    # Check if openclaw CLI is available
    openclaw_bin = shutil.which("openclaw")
    if not openclaw_bin:
        print("   ⚠️  `openclaw` CLI not found in PATH")
        print("   Manual install: openclaw hooks install " + str(nima_root))
        return False
    
    # Check if hooks already exist
    hooks_dir = Path.home() / ".openclaw" / "hooks"
    existing = []
    for hook_name in ["nima-bootstrap", "nima-recall"]:
        if (hooks_dir / hook_name).exists():
            existing.append(hook_name)
    
    if existing:
        print(f"   Found existing hooks: {', '.join(existing)}")
        response = input("   Overwrite? [y/N]: ").strip().lower()
        if response not in ('y', 'yes'):
            print("   Keeping existing hooks.")
            return True
        # Remove existing so install doesn't fail
        for hook_name in existing:
            hook_path = hooks_dir / hook_name
            if hook_path.exists():
                try:
                    shutil.rmtree(hook_path)
                    print(f"   Removed old {hook_name}")
                except OSError as e:
                    print(f"   ❌ Failed to remove {hook_name} at {hook_path}: {e}")
                    print("   Cannot continue hook installation.")
                    return False
    
    # Run openclaw hooks install
    try:
        result = subprocess.run(
            [openclaw_bin, "hooks", "install", str(nima_root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            print("   ✅ Hooks installed!")
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    print(f"   {line}")
            return True
        else:
            print(f"   ❌ Install failed: {result.stderr.strip() or result.stdout.strip()}")
            print(f"   Manual install: openclaw hooks install {nima_root}")
            return False
    except FileNotFoundError:
        print("   ❌ openclaw CLI not found")
        return False
    except subprocess.TimeoutExpired:
        print("   ❌ Install timed out")
        return False


def enable_hooks() -> bool:
    """Enable the installed hooks. Returns True only if all succeeded."""
    openclaw_bin = shutil.which("openclaw")
    if not openclaw_bin:
        return False
    
    all_enabled = True
    for hook_name in ["nima-bootstrap", "nima-recall"]:
        try:
            result = subprocess.run(
                [openclaw_bin, "hooks", "enable", hook_name],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                print(f"   ✅ {hook_name} enabled")
            else:
                print(f"   ⚠️  {hook_name}: {result.stderr.strip() or 'enable failed'}")
                all_enabled = False
        except (subprocess.SubprocessError, OSError) as e:
            print(f"   ⚠️  {hook_name}: {e}")
            all_enabled = False
    
    return all_enabled


def setup_agents_md(workspace: str) -> bool:
    """Add NIMA instructions to AGENTS.md if not already present."""
    agents_path = Path(workspace) / "AGENTS.md"
    
    nima_block = """
## 🧠 NIMA Memory

You have persistent memory via NIMA. Use it:

**Capture important moments:**
```bash
python3 -c "from nima_core import NimaCore; n = NimaCore(); n.capture('someone', 'said something important', importance=0.8)"
```

**Search memories:**
```bash
python3 -c "from nima_core import NimaCore; n = NimaCore(); [print(f'{r[\"who\"]}: {r[\"what\"]}') for r in n.recall('query', top_k=5)]"
```

**Dream consolidation** runs automatically via cron (2 AM daily).

Memories are auto-recalled on session start via the nima-recall hook.
"""
    
    if agents_path.exists():
        content = agents_path.read_text()
        if "NIMA" in content and "NimaCore" in content:
            print("   ℹ️  AGENTS.md already has NIMA instructions")
            return True
        
        # Append
        with open(agents_path, "a") as f:
            f.write("\n" + nima_block)
        print("   ✅ Added NIMA instructions to AGENTS.md")
    else:
        agents_path.write_text("# AGENTS.md\n" + nima_block)
        print("   ✅ Created AGENTS.md with NIMA instructions")
    
    return True


def setup_cron_consolidation() -> bool:
    """Set up dream consolidation cron job if openclaw supports it."""
    openclaw_bin = shutil.which("openclaw")
    if not openclaw_bin:
        print("   ℹ️  Set up a cron job manually to run nightly:")
        print("      python3 -c \"from nima_core import NimaCore; NimaCore().dream(hours=24)\"")
        return False
    
    print("   ℹ️  To add dream consolidation, tell your agent:")
    print("      'Set up a cron job at 2 AM daily to run NIMA dream consolidation'")
    print("   Or add it via the OpenClaw cron system.")
    return True


def run_setup():
    """Run interactive setup wizard."""
    print("🧠 NIMA Setup Wizard")
    print("=" * 50)
    
    # Step 1: Detect environment
    openclaw = detect_openclaw()
    
    if openclaw:
        print("✅ OpenClaw detected!")
        print(f"   Workspace: {openclaw['workspace']}")
        print(f"   Version: {openclaw.get('version', 'unknown')}")
    else:
        print("ℹ️  OpenClaw not detected — running in standalone mode")
    print()
    
    # Step 2: Configure paths
    config = get_nima_config()
    print(f"📁 Data directory: {config['data_dir']}")
    print(f"📁 Models directory: {config['models_dir']}")
    print()
    
    # Confirm
    response = input("Proceed with setup? [Y/n]: ").strip().lower()
    if response not in ('', 'y', 'yes'):
        print("Setup cancelled.")
        sys.exit(0)
    
    # Step 3: Create directories
    print("\n🔧 Creating directories...")
    setup_paths(config)
    print("✅ Directories created")
    
    # Step 4: Save config
    config_path = Path(config['data_dir']) / "config.json"
    try:
        from ..utils import atomic_json_save
        atomic_json_save(config, config_path)
        print(f"✅ Config saved to {config_path}")
    except (OSError, ImportError):
        # Fallback: direct write
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"✅ Config saved to {config_path}")
    
    # Step 5: OpenClaw integration (the magic)
    if openclaw:
        print("\n" + "=" * 50)
        print("🔗 OpenClaw Integration")
        print("=" * 50)
        
        nima_root = find_nima_core_root()
        
        # 5a: Install hooks
        hooks_ok = install_hooks(nima_root)
        
        # 5b: Enable hooks
        if hooks_ok:
            enable_hooks()
        
        # 5c: Update AGENTS.md
        print("\n📝 Agent configuration...")
        setup_agents_md(openclaw['workspace'])
        
        # 5d: Cron for consolidation
        print("\n⏰ Dream consolidation...")
        setup_cron_consolidation()
        
        # 5e: Restart suggestion
        print("\n🔄 Restart OpenClaw to activate hooks:")
        print("   openclaw gateway restart")
    
    # Summary
    print("\n" + "=" * 50)
    print("✨ Setup complete!")
    print(f"   Mode: {config['mode']}")
    
    if openclaw:
        print("\n   What was set up:")
        print("   • NIMA data directories")
        if hooks_ok:
            print("   • Bootstrap hook (injects memory status)")
            print("   • Recall hook (surfaces relevant memories)")
        else:
            print("   • ⚠️  Hooks not installed — retry with:")
            print("     openclaw hooks install /path/to/nima-core")
        print("   • AGENTS.md instructions for your agent")
        print("\n   Next steps:")
        print("   1. Restart OpenClaw: openclaw gateway restart")
        print("   2. Chat with your agent — it now has memory! 🧠")
    else:
        print("\n   Use NIMA in Python:")
        print("   >>> from nima_core import NimaCore")
        print("   >>> nima = NimaCore()")
        print("   >>> nima.experience('User asked about weather', who='user')")
        print("   >>> nima.recall('weather')")
    
    print()


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="NIMA — Noosphere Integrated Memory Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nima-core              # Interactive setup wizard
  nima-core init         # Same as above
  
After setup, restart OpenClaw:
  openclaw gateway restart
        """,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="init",
        choices=["init"],
        help="Command to run (default: init)",
    )
    
    args = parser.parse_args()
    
    if args.command == "init":
        run_setup()


if __name__ == "__main__":
    main()
