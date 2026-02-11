#!/usr/bin/env python3
"""
Marker PDF OCR - CLI Tool for OpenClaw
Local-first PDF to Markdown conversion
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.marker_ocr_service import (
    MarkerOCRService, 
    DeploymentMode,
    ErrorClassification
)


def cmd_convert(args) -> int:
    """Convert PDF to Markdown"""
    try:
        service = MarkerOCRService()
        
        # Validate PDF path
        if not Path(args.pdf_path).exists():
            error_response = {
                "error": "FileNotFoundError",
                "message": f"PDF not found: {args.pdf_path}",
                "suggestion": "Check if file path is correct and accessible"
            }
            print(json.dumps(error_response, indent=2), file=sys.stderr)
            return 1
        
        # Auto-detect mode if not specified
        mode = args.mode or os.getenv("MARKER_DEPLOYMENT_MODE", "auto")
        
        print(f"🔄 Converting: {Path(args.pdf_path).name}")
        print(f"📍 Mode: {mode}")
        print(f"📄 Format: {args.format}")
        
        result = service.convert(
            pdf_path=args.pdf_path,
            mode=mode,
            output_format=args.format,
            timeout=args.timeout
        )
        
        # Output result
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result.content)
            print(f"\n✅ Saved to: {args.output}")
        else:
            print("\n" + "="*60)
            print(result.content)
            print("="*60)
        
        # Print metadata
        print(f"\n📊 Stats:")
        print(f"   Mode used: {result.mode_used}")
        print(f"   Pages: {result.pages}")
        print(f"   Time: {result.processing_time:.2f}s")
        
        return 0
        
    except Exception as e:
        error_type = type(e).__name__
        suggestion = _get_error_suggestion(e)
        
        error_response = {
            "error": error_type,
            "message": str(e),
            "suggestion": suggestion,
            "mode_suggestion": _get_mode_suggestion(e)
        }
        
        # Check if we should suggest mode switch
        if ErrorClassification.classify(e) == "mode_switch":
            print(f"\n⚠️  {e}", file=sys.stderr)
            print(f"💡 Suggestion: {suggestion}", file=sys.stderr)
            if "local" in str(e).lower():
                print("   Try: marker-ocr convert <file> --mode cloud", file=sys.stderr)
            else:
                print("   Try: marker-ocr convert <file> --mode local", file=sys.stderr)
        else:
            print(json.dumps(error_response, indent=2), file=sys.stderr)
        
        return 1


def cmd_health_check(args) -> int:
    """Check system health and available modes"""
    try:
        service = MarkerOCRService()
        health = service.health_check()
        
        if args.verbose:
            print(json.dumps(health, indent=2))
        else:
            status = "✅" if health["healthy"] else "❌"
            print(f"{status} Health Status: {'Healthy' if health['healthy'] else 'Unhealthy'}")
            print(f"\n📊 System Info:")
            print(f"   Available memory: {health['memory_available_mb']:,} MB")
            print(f"   Available modes: {', '.join(health['available_modes']) or 'None'}")
            print(f"   Recommended mode: {health['recommended_mode']}")
            
            print(f"\n🔌 Mode Status:")
            print(f"   Local (CPU): {'✅ Ready' if health['local_ready'] else '❌ Not installed'}")
            print(f"   Cloud (API): {'✅ Ready' if health['cloud_ready'] else '❌ No API key'}")
            
            if not health["local_ready"]:
                print(f"\n💡 To enable local mode:")
                print(f"   marker-ocr install-local")
            
            if not health["cloud_ready"]:
                print(f"\n💡 To enable cloud mode:")
                print(f"   export MARKER_API_KEY='your-key'")
        
        return 0 if health["healthy"] else 1
        
    except Exception as e:
        print(f"❌ Health check failed: {e}", file=sys.stderr)
        return 1


def cmd_install_local(args) -> int:
    """Install local dependencies"""
    print("📦 Installing marker-pdf (CPU-only)...")
    print("   This will download ~2GB of dependencies.")
    print("   Estimated time: 5-10 minutes depending on network.\n")
    
    if not args.yes:
        try:
            confirm = input("Continue? [y/N]: ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return 0
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 0
    
    service = MarkerOCRService()
    
    print("⏳ Installing... (this may take a while)")
    success = service.install_local()
    
    if success:
        print("\n✅ Installation complete!")
        print("🧪 Verifying installation...")
        
        health = service.health_check()
        if health["local_ready"]:
            print("✅ Local mode is ready!")
            print("\n📝 Quick test:")
            print("   marker-ocr health-check")
            return 0
        else:
            print("⚠️ Installation completed but verification failed.")
            print("   Try: marker-ocr health-check --verbose")
            return 1
    else:
        print("\n❌ Installation failed.", file=sys.stderr)
        print("   Common causes:", file=sys.stderr)
        print("   - Network timeout (retry)", file=sys.stderr)
        print("   - Insufficient disk space (need ~5GB)", file=sys.stderr)
        print("   - Permission denied (try with sudo)", file=sys.stderr)
        return 1


def _get_error_suggestion(error: Exception) -> str:
    """Get user-friendly error suggestion"""
    error_type = type(error).__name__
    
    suggestions = {
        "MemoryError": "Try --mode cloud or increase MARKER_MAX_MEMORY_MB",
        "FileNotFoundError": "Check if PDF file exists and is readable",
        "PermissionError": "Check file permissions",
        "TimeoutError": "Try increasing --timeout or use cloud mode",
        "RuntimeError": "Check error message for specific guidance",
        "ValueError": "Check PDF is valid and not corrupted",
        "ConnectionError": "Check internet connection for cloud mode",
    }
    
    return suggestions.get(error_type, "Check logs or try different mode")


def _get_mode_suggestion(error: Exception) -> Optional[str]:
    """Suggest alternative mode on failure"""
    error_msg = str(error).lower()
    
    if "memory" in error_msg or "oom" in error_msg:
        return "Use --mode cloud for large documents"
    elif "api" in error_msg or "quota" in error_msg:
        return "Use --mode local to avoid API limits"
    elif "marker" in error_msg and "not" in error_msg:
        return "Run 'marker-ocr install-local' to enable local mode"
    
    return None


def main():
    parser = argparse.ArgumentParser(
        prog='marker-ocr',
        description='Convert PDF to Markdown using Marker OCR (local-first)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  marker-ocr convert paper.pdf
  marker-ocr convert paper.pdf --mode local --format json
  marker-ocr convert paper.pdf --mode cloud --output result.md
  marker-ocr health-check --verbose
  marker-ocr install-local --yes

Environment Variables:
  MARKER_API_KEY        API key for cloud mode (optional)
  MARKER_DEPLOYMENT_MODE  Default mode: auto/local/cloud (default: auto)
  MARKER_MAX_MEMORY_MB    Memory limit in MB (default: 4096)
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # convert command
    convert_parser = subparsers.add_parser('convert', help='Convert PDF to Markdown')
    convert_parser.add_argument('pdf_path', help='Path to input PDF file')
    convert_parser.add_argument('--mode', choices=['auto', 'local', 'cloud'],
                               default='auto', help='Deployment mode (default: auto)')
    convert_parser.add_argument('--format', choices=['markdown', 'json', 'html'],
                               default='markdown', help='Output format')
    convert_parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    convert_parser.add_argument('--timeout', type=int, default=300,
                               help='Processing timeout in seconds (default: 300)')
    
    # health-check command
    health_parser = subparsers.add_parser('health-check', help='Check system health')
    health_parser.add_argument('--verbose', '-v', action='store_true',
                              help='Show detailed diagnostics')
    
    # install-local command
    install_parser = subparsers.add_parser('install-local',
                                          help='Install local dependencies')
    install_parser.add_argument('--yes', '-y', action='store_true',
                               help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to command handler
    commands = {
        'convert': cmd_convert,
        'health-check': cmd_health_check,
        'install-local': cmd_install_local
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
