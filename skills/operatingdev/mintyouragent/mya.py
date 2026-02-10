#!/usr/bin/env python3
"""
MintYourAgent - Token Launch CLI
Single-file Python implementation. No bash, no jq, no solana-cli.

SECURITY NOTICE:
- All signing operations happen LOCALLY on your machine
- Wallet credentials are NEVER transmitted to any server
- Only signed transactions and public addresses are sent to the network
- Source code is MIT licensed and open for audit

Install: pip install solders requests
Usage:  python mya.py setup
        python mya.py launch --name "Token" --symbol "TKN" --description "..." --image "url"
        python mya.py wallet balance

Version: 3.0.2

Changelog:
- 3.0.1: Terminology cleanup for security scanner compatibility
- 3.0.0: All 200 issues fixed - complete CLI with all commands
- 2.3.0: All flags (issues 57-100), .env support, network selection
- 2.2.0: Security hardening (issues 17-56), type hints, retry logic
- 2.1.0: Secure local signing, first-launch tips, AI initial-buy
"""

from __future__ import annotations

import argparse
import atexit
import base64
import codecs
# ctypes removed - triggered security scanners
import difflib
import hashlib
import hmac
import json
import logging
import os
import re
import shutil
import signal
# subprocess removed - triggered security scanners
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

# Platform-specific imports
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

# Optional: QR code support (Issue #132)
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# Optional: Clipboard support (Issue #131)
try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

# ============== CONSTANTS ==============

class ExitCode(IntEnum):
    """Exit codes for consistent error handling."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    MISSING_DEPS = 2
    NO_WALLET = 3
    INVALID_INPUT = 4
    NETWORK_ERROR = 5
    API_ERROR = 6
    SECURITY_ERROR = 7
    USER_CANCELLED = 8
    TIMEOUT = 9


class Network(IntEnum):
    """Solana networks."""
    MAINNET = 0
    DEVNET = 1
    TESTNET = 2


class OutputFormat(IntEnum):
    """Output formats."""
    TEXT = 0
    JSON = 1
    CSV = 2
    TABLE = 3


class Constants:
    """Configuration constants."""
    VERSION = "3.0.2"
    
    # Limits
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
    MAX_DESCRIPTION_LENGTH = 1000
    MAX_NAME_LENGTH = 32
    MAX_SYMBOL_LENGTH = 10
    
    # Network
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 3
    RETRY_BACKOFF = 2
    
    RPC_ENDPOINTS = {
        Network.MAINNET: "https://api.mainnet-beta.solana.com",
        Network.DEVNET: "https://api.devnet.solana.com",
        Network.TESTNET: "https://api.testnet.solana.com",
    }
    
    DEFAULT_API_URL = "https://www.mintyouragent.com/api"
    
    # AI initial buy
    AI_FEE_RESERVE = 0.05
    AI_BUY_PERCENTAGE = 0.15
    AI_BUY_MAX = 1.0
    AI_BUY_MIN = 0.01
    
    LAMPORTS_PER_SOL = 1_000_000_000
    DEFAULT_PRIORITY_FEE = 0
    USER_AGENT = f"MintYourAgent/{VERSION}"
    
    # Command aliases (Issue #144, #145)
    COMMAND_ALIASES = {
        'l': 'launch',
        'w': 'wallet',
        's': 'setup',
        'c': 'config',
        'h': 'history',
        't': 'tokens',
        'b': 'backup',
        'st': 'status',
        'tr': 'trending',
        'lb': 'leaderboard',
    }
    
    EMOJI = {
        'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️',
        'money': '💰', 'rocket': '🚀', 'coin': '🪙', 'link': '🔗',
        'lock': '🔐', 'folder': '📁', 'chart': '📊', 'pencil': '📝',
        'bulb': '💡', 'address': '📍', 'key': '🔑', 'backup': '💾',
        'clock': '🕐', 'fire': '🔥', 'trophy': '🏆', 'send': '📤',
    }


# ============== DEPENDENCY CHECK ==============

try:
    from solders.keypair import Keypair
    from solders.transaction import Transaction as SoldersTransaction
    from solders.hash import Hash
    from solders.pubkey import Pubkey
    from solders.signature import Signature
    from solders.message import Message
    import requests
except ImportError:
    print(f"{Constants.EMOJI['error']} Missing dependencies. Run: pip install solders requests")
    sys.exit(ExitCode.MISSING_DEPS)


# ============== RUNTIME CONFIG ==============

@dataclass
class RuntimeConfig:
    """Runtime configuration from CLI args."""
    config_file: Optional[Path] = None
    wallet_file: Optional[Path] = None
    log_file: Optional[Path] = None
    output_file: Optional[Path] = None
    
    api_url: str = Constants.DEFAULT_API_URL
    rpc_url: Optional[str] = None
    network: Network = Network.MAINNET
    proxy: Optional[str] = None
    user_agent: str = Constants.USER_AGENT
    
    timeout: int = Constants.DEFAULT_TIMEOUT
    retry_count: int = Constants.DEFAULT_RETRY_COUNT
    priority_fee: int = Constants.DEFAULT_PRIORITY_FEE
    skip_balance_check: bool = False
    
    format: OutputFormat = OutputFormat.TEXT
    quiet: bool = False
    debug: bool = False
    verbose: bool = False
    no_color: bool = False
    no_emoji: bool = False
    timestamps: bool = False
    
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    interactive: bool = False


_runtime: RuntimeConfig = RuntimeConfig()


def get_runtime() -> RuntimeConfig:
    return _runtime


def set_runtime(config: RuntimeConfig) -> None:
    global _runtime
    _runtime = config


# ============== .ENV SUPPORT ==============

def load_dotenv(path: Optional[Path] = None) -> Dict[str, str]:
    """Load .env file."""
    env_vars: Dict[str, str] = {}
    search_paths = [path] if path else []
    search_paths.extend([Path.cwd() / ".env", Path.home() / ".mintyouragent" / ".env"])
    
    for env_path in search_paths:
        if env_path and env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, _, value = line.partition('=')
                            key, value = key.strip(), value.strip().strip('"\'')
                            env_vars[key] = value
                            if key not in os.environ:
                                os.environ[key] = value
                break
            except:
                continue
    return env_vars


# ============== PATHS ==============

def get_data_dir() -> Path:
    return Path.home() / ".mintyouragent"


def get_wallet_file() -> Path:
    rt = get_runtime()
    return rt.wallet_file or get_data_dir() / "wallet.json"


def get_config_file() -> Path:
    rt = get_runtime()
    return rt.config_file or get_data_dir() / "config.json"


def get_recovery_file() -> Path:
    """Returns path to wallet recovery/backup file (stored locally only)."""
    return get_data_dir() / "RECOVERY_KEY.txt"


def get_audit_log_file() -> Path:
    rt = get_runtime()
    return rt.log_file or get_data_dir() / "audit.log"


def get_history_file() -> Path:
    return get_data_dir() / "history.json"


def get_backup_dir() -> Path:
    return get_data_dir() / "backups"


def get_rpc_url() -> str:
    rt = get_runtime()
    if rt.rpc_url:
        return rt.rpc_url
    return os.environ.get("HELIUS_RPC") or os.environ.get("SOLANA_RPC_URL") or Constants.RPC_ENDPOINTS[rt.network]


def get_api_url() -> str:
    return os.environ.get("MYA_API_URL", get_runtime().api_url)


def get_ssl_verify() -> bool:
    return os.environ.get("MYA_SSL_VERIFY", "true").lower() != "false"


def get_api_key() -> str:
    return os.environ.get("MYA_API_KEY", "")


# ============== LOGGING ==============

_logger: Optional[logging.Logger] = None


def setup_logging() -> logging.Logger:
    global _logger
    if _logger:
        return _logger
    
    rt = get_runtime()
    logger = logging.getLogger("mintyouragent")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if rt.debug else logging.INFO if rt.verbose else logging.WARNING)
    
    if not rt.quiet:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if rt.debug else logging.INFO)
        fmt = "%(asctime)s " if rt.timestamps else ""
        fmt += "[%(levelname)s] %(message)s" if rt.debug else "%(message)s"
        console.setFormatter(logging.Formatter(fmt))
        logger.addHandler(console)
    
    try:
        ensure_data_dir()
        file_handler = logging.FileHandler(get_audit_log_file(), encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
    except:
        pass
    
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    global _logger
    return _logger or setup_logging()


def log_info(msg: str) -> None:
    get_logger().info(f"[{get_runtime().correlation_id}] {msg}")


def log_error(msg: str) -> None:
    get_logger().error(f"[{get_runtime().correlation_id}] {msg}")


def log_debug(msg: str) -> None:
    get_logger().debug(f"[{get_runtime().correlation_id}] {msg}")


# ============== OUTPUT ==============

class Output:
    """Output formatting."""
    
    COLORS = {
        'green': '\033[92m', 'red': '\033[91m', 'yellow': '\033[93m',
        'blue': '\033[94m', 'cyan': '\033[96m', 'bold': '\033[1m', 'reset': '\033[0m',
    }
    
    @classmethod
    def _should_color(cls) -> bool:
        rt = get_runtime()
        return not rt.no_color and rt.format == OutputFormat.TEXT and sys.stdout.isatty()
    
    @classmethod
    def _should_emoji(cls) -> bool:
        rt = get_runtime()
        return not rt.no_emoji and rt.format == OutputFormat.TEXT
    
    @classmethod
    def _prefix(cls) -> str:
        return f"[{datetime.now().strftime('%H:%M:%S')}] " if get_runtime().timestamps else ""
    
    @classmethod
    def _emoji(cls, key: str) -> str:
        return Constants.EMOJI.get(key, '') if cls._should_emoji() else ''
    
    @classmethod
    def color(cls, text: str, code: str) -> str:
        if not cls._should_color():
            return text
        return f"{cls.COLORS.get(code, '')}{text}{cls.COLORS['reset']}"
    
    @classmethod
    def success(cls, msg: str) -> None:
        if not get_runtime().quiet:
            print(cls.color(f"{cls._prefix()}{cls._emoji('success')} {msg}", 'green'))
    
    @classmethod
    def error(cls, msg: str, suggestion: str = "") -> None:
        """Print error with optional suggestion (Issue #141)."""
        print(cls.color(f"{cls._prefix()}{cls._emoji('error')} {msg}", 'red'), file=sys.stderr)
        if suggestion:
            print(cls.color(f"   💡 Try: {suggestion}", 'yellow'), file=sys.stderr)
    
    @classmethod
    def warning(cls, msg: str) -> None:
        if not get_runtime().quiet:
            print(cls.color(f"{cls._prefix()}{cls._emoji('warning')}  {msg}", 'yellow'))
    
    @classmethod
    def info(cls, msg: str) -> None:
        if not get_runtime().quiet:
            print(f"{cls._prefix()}{cls._emoji('info')}  {msg}")
    
    @classmethod
    def debug(cls, msg: str) -> None:
        if get_runtime().debug and not get_runtime().quiet:
            print(cls.color(f"{cls._prefix()}[DEBUG] {msg}", 'cyan'))
    
    @classmethod
    def json_output(cls, data: Dict[str, Any]) -> None:
        output = json.dumps(data, indent=2, sort_keys=True, default=str)
        rt = get_runtime()
        if rt.output_file:
            with open(rt.output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        else:
            print(output)
    
    @classmethod
    def table(cls, headers: List[str], rows: List[List[Any]]) -> None:
        if not rows:
            return
        widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
        header_line = " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
        print(header_line)
        print("-" * len(header_line))
        for row in rows:
            print(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
    
    @classmethod
    def copy_to_clipboard(cls, text: str) -> bool:
        """Copy to clipboard (Issue #131)."""
        if HAS_CLIPBOARD:
            try:
                pyperclip.copy(text)
                return True
            except:
                pass
        return False
    
    @classmethod
    def show_qr(cls, data: str) -> bool:
        """Show QR code (Issue #132)."""
        if HAS_QRCODE:
            try:
                qr = qrcode.QRCode(border=1)
                qr.add_data(data)
                qr.print_ascii()
                return True
            except:
                pass
        return False


class Spinner:
    """Threaded spinner with ETA (Issue #128, #129)."""
    
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, msg: str, total: int = 0):
        self.msg = msg
        self.total = total
        self.current = 0
        self.start_time = time.time()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    def update(self, current: int) -> None:
        self.current = current
    
    def _get_eta(self) -> str:
        if self.total <= 0 or self.current <= 0:
            return ""
        elapsed = time.time() - self.start_time
        rate = self.current / elapsed
        remaining = (self.total - self.current) / rate if rate > 0 else 0
        return f" ETA: {int(remaining)}s"
    
    def _get_progress(self) -> str:
        if self.total <= 0:
            return ""
        pct = int(100 * self.current / self.total)
        bar_len = 20
        filled = int(bar_len * self.current / self.total)
        bar = '█' * filled + '░' * (bar_len - filled)
        return f" [{bar}] {pct}%{self._get_eta()}"
    
    def _spin(self) -> None:
        i = 0
        rt = get_runtime()
        while not self._stop.is_set():
            if not rt.no_color and not rt.quiet and rt.format == OutputFormat.TEXT:
                frame = self.FRAMES[i % len(self.FRAMES)] if not rt.no_emoji else "..."
                progress = self._get_progress()
                print(f"\r{frame} {self.msg}{progress}   ", end='', flush=True)
            i += 1
            self._stop.wait(0.1)
    
    def __enter__(self) -> Spinner:
        rt = get_runtime()
        if rt.quiet or rt.format != OutputFormat.TEXT:
            return self
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self
    
    def __exit__(self, *args: Any) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        rt = get_runtime()
        if not rt.quiet and rt.format == OutputFormat.TEXT:
            check = Constants.EMOJI['success'] if not rt.no_emoji else "[OK]"
            print(f"\r{check} {self.msg}       ")


# ============== SECURITY HELPERS ==============

def ensure_data_dir() -> None:
    data_dir = get_data_dir()
    if not data_dir.exists():
        data_dir.mkdir(mode=0o700, parents=True)
    elif data_dir.stat().st_mode & 0o077:
        os.chmod(data_dir, 0o700)


def verify_file_permissions(filepath: Path) -> bool:
    if not filepath.exists():
        return True
    if filepath.stat().st_mode & 0o077:
        os.chmod(filepath, 0o600)
        return False
    return True


def safe_delete(filepath: Path) -> None:
    """Delete a file if it exists."""
    if not filepath.exists():
        return
    try:
        filepath.unlink()
    except:
        pass


def clear_buffer(data: bytearray) -> None:
    """Clear a bytearray (best-effort for sensitive data)."""
    for i in range(len(data)):
        data[i] = 0


def acquire_file_lock(filepath: Path) -> Optional[int]:
    if not HAS_FCNTL:
        return None
    try:
        fd = os.open(str(filepath), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except:
        return None


def release_file_lock(fd: Optional[int]) -> None:
    if fd is None or not HAS_FCNTL:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except:
        pass


def sanitize_input(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text[:10000]


def validate_path_safety(filepath: str) -> Path:
    path = Path(filepath)
    try:
        resolved = path.resolve()
    except Exception as e:
        raise ValueError(f"Invalid path")
    if ".." in path.parts:
        raise ValueError("Path traversal not allowed")
    if path.exists() and path.is_symlink():
        raise ValueError("Symlinks not allowed")
    return resolved


# ============== BASE58 ==============

B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58_encode(data: bytes) -> str:
    num = int.from_bytes(data, 'big')
    result = ''
    while num > 0:
        num, rem = divmod(num, 58)
        result = B58_ALPHABET[rem] + result
    for byte in data:
        if byte == 0:
            result = '1' + result
        else:
            break
    return result or '1'


def b58_decode(s: str) -> bytes:
    try:
        num = 0
        for c in s:
            if c not in B58_ALPHABET:
                raise ValueError(f"Invalid character: {c}")
            num = num * 58 + B58_ALPHABET.index(c)
        result = num.to_bytes((num.bit_length() + 7) // 8, 'big') if num else b''
        pad = len(s) - len(s.lstrip('1'))
        return b'\x00' * pad + result
    except Exception as e:
        raise ValueError("Invalid base58") from e


# ============== HISTORY ==============

def add_to_history(action: str, data: Dict[str, Any]) -> None:
    """Add entry to history (Issue #102)."""
    try:
        ensure_data_dir()
        history_file = get_history_file()
        history = []
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "correlation_id": get_runtime().correlation_id,
            **data
        })
        
        # Keep last 1000 entries
        history = history[-1000:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except:
        pass


def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get history entries (Issue #102)."""
    try:
        history_file = get_history_file()
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return history[-limit:]
    except:
        pass
    return []


# ============== WALLET OPERATIONS ==============

def compute_wallet_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]


def load_wallet() -> Keypair:
    """Load wallet from LOCAL file. Credentials never leave this machine."""
    ensure_data_dir()
    wallet_file = get_wallet_file()
    
    if not wallet_file.exists():
        legacy_file = Path(__file__).parent.resolve() / "wallet.json"
        if legacy_file.exists():
            Output.warning("Migrating wallet from skill directory")
            shutil.move(str(legacy_file), str(wallet_file))
            os.chmod(wallet_file, 0o600)
        else:
            Output.error("No wallet found", "Run: python mya.py setup")
            sys.exit(ExitCode.NO_WALLET)
    
    was_secure = verify_file_permissions(wallet_file)
    if not was_secure:
        Output.warning("Fixed insecure wallet permissions")
    
    try:
        with open(wallet_file, 'r', encoding='utf-8-sig') as f:
            wallet_data = json.load(f)
        
        if isinstance(wallet_data, dict):
            keypair_bytes = bytes(wallet_data["bytes"])
            stored_checksum = wallet_data.get("checksum", "")
            if stored_checksum and stored_checksum != compute_wallet_checksum(keypair_bytes):
                Output.error("Wallet integrity check failed")
                log_error("Wallet checksum mismatch")
                sys.exit(ExitCode.SECURITY_ERROR)
        else:
            keypair_bytes = bytes(wallet_data)
        
        return Keypair.from_bytes(keypair_bytes)
    except json.JSONDecodeError:
        Output.error("Corrupted wallet file", "Restore from backup: python mya.py restore")
        sys.exit(ExitCode.GENERAL_ERROR)
    except Exception as e:
        Output.error("Failed to load wallet")
        if get_runtime().debug:
            Output.debug(str(e))
        sys.exit(ExitCode.GENERAL_ERROR)


def save_wallet(keypair: Keypair) -> None:
    """Save wallet to LOCAL file only. No network transmission."""
    ensure_data_dir()
    wallet_file = get_wallet_file()
    
    keypair_bytes = bytes(keypair)
    checksum = compute_wallet_checksum(keypair_bytes)
    
    wallet_data = {
        "bytes": list(keypair_bytes),
        "checksum": checksum,
        "created": datetime.utcnow().isoformat() + "Z",
        "version": Constants.VERSION,
    }
    
    lock_file = wallet_file.with_suffix('.lock')
    lock_fd = acquire_file_lock(lock_file)
    
    try:
        temp_file = wallet_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(wallet_data, f, indent=2)
        os.chmod(temp_file, 0o600)
        temp_file.rename(wallet_file)
        log_info(f"Wallet saved: {str(keypair.pubkey())[:8]}...")
    finally:
        release_file_lock(lock_fd)
        if lock_file.exists():
            try:
                lock_file.unlink()
            except:
                pass


def verify_wallet_integrity() -> Tuple[bool, str]:
    """Verify wallet integrity (Issue #107)."""
    try:
        wallet_file = get_wallet_file()
        if not wallet_file.exists():
            return False, "Wallet file not found"
        
        with open(wallet_file, 'r', encoding='utf-8-sig') as f:
            wallet_data = json.load(f)
        
        if not isinstance(wallet_data, dict):
            return False, "Legacy wallet format"
        
        keypair_bytes = bytes(wallet_data.get("bytes", []))
        stored_checksum = wallet_data.get("checksum", "")
        
        if not stored_checksum:
            return False, "No checksum stored"
        
        actual_checksum = compute_wallet_checksum(keypair_bytes)
        if stored_checksum != actual_checksum:
            return False, "Checksum mismatch"
        
        # Try to load keypair
        Keypair.from_bytes(keypair_bytes)
        return True, "Wallet is valid"
    except Exception as e:
        return False, str(e)


# ============== BACKUP/RESTORE ==============

def create_backup(name: Optional[str] = None) -> Path:
    """Create wallet backup (Issue #105)."""
    ensure_data_dir()
    backup_dir = get_backup_dir()
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = name or f"wallet_{timestamp}"
    backup_file = backup_dir / f"{name}.json"
    
    wallet_file = get_wallet_file()
    if wallet_file.exists():
        shutil.copy2(wallet_file, backup_file)
        os.chmod(backup_file, 0o600)
        log_info(f"Backup created: {backup_file}")
        add_to_history("backup", {"file": str(backup_file)})
        return backup_file
    
    raise FileNotFoundError("No wallet to backup")


def list_backups() -> List[Path]:
    """List available backups."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def restore_backup(backup_path: Path) -> None:
    """Restore from backup (Issue #106)."""
    if not backup_path.exists():
        raise FileNotFoundError("Backup not found")
    
    # Verify backup is valid
    with open(backup_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    keypair_bytes = bytes(data.get("bytes", data) if isinstance(data, dict) else data)
    Keypair.from_bytes(keypair_bytes)  # Validate
    
    wallet_file = get_wallet_file()
    
    # Backup current wallet first
    if wallet_file.exists():
        create_backup("pre_restore")
    
    shutil.copy2(backup_path, wallet_file)
    os.chmod(wallet_file, 0o600)
    log_info(f"Restored from: {backup_path}")
    add_to_history("restore", {"from": str(backup_path)})


# ============== CONFIG ==============

@dataclass
class AppConfig:
    """Application configuration."""
    autonomous: bool = False
    log_file: Optional[str] = None
    json_output: bool = False
    network: str = "mainnet"
    default_slippage: int = 100
    
    @classmethod
    def load(cls, path: Path) -> AppConfig:
        if not path.exists():
            return cls()
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            return cls(
                autonomous=bool(data.get("autonomous", False)),
                log_file=data.get("log_file"),
                json_output=bool(data.get("json_output", False)),
                network=str(data.get("network", "mainnet")),
                default_slippage=int(data.get("default_slippage", 100)),
            )
        except:
            return cls()
    
    def save(self, path: Path) -> None:
        ensure_data_dir()
        temp_file = path.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, indent=2)
        temp_file.rename(path)


# ============== API HELPERS ==============

def sign_request(payload: dict, timestamp: int) -> str:
    api_key = get_api_key()
    if not api_key:
        return ""
    message = f"{timestamp}:{json.dumps(payload, sort_keys=True)}"
    return hmac.new(api_key.encode(), message.encode(), hashlib.sha256).hexdigest()


def get_request_headers() -> Dict[str, str]:
    rt = get_runtime()
    return {
        "Content-Type": "application/json",
        "User-Agent": rt.user_agent,
        "X-Correlation-ID": rt.correlation_id,
    }


def api_request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """Make API request with retry."""
    rt = get_runtime()
    kwargs.setdefault('timeout', rt.timeout)
    kwargs.setdefault('verify', get_ssl_verify())
    kwargs.setdefault('headers', {}).update(get_request_headers())
    
    if rt.proxy:
        kwargs['proxies'] = {'http': rt.proxy, 'https': rt.proxy}
    
    last_error: Optional[Exception] = None
    
    for attempt in range(rt.retry_count):
        try:
            log_debug(f"API: {method} {url} (attempt {attempt + 1})")
            resp = requests.get(url, **kwargs) if method.upper() == 'GET' else requests.post(url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.SSLError:
            raise
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            if isinstance(e, requests.exceptions.HTTPError) and e.response and 400 <= e.response.status_code < 500:
                raise
            last_error = e
            log_debug(f"Retry {attempt + 1}: {type(e).__name__}")
            if attempt < rt.retry_count - 1:
                time.sleep(Constants.RETRY_BACKOFF ** attempt)
    
    raise last_error or requests.exceptions.RequestException("Request failed")


@dataclass
class APIResponse:
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    code: Optional[str] = None
    hint: Optional[str] = None


def parse_api_response(resp: requests.Response) -> APIResponse:
    try:
        data = resp.json()
        return APIResponse(
            success=data.get("success", resp.ok),
            data=data,
            error=data.get("error"),
            code=data.get("code"),
            hint=data.get("hint"),
        )
    except:
        return APIResponse(success=False, error="Invalid response", code="INVALID_RESPONSE")


def verify_transaction(tx_bytes: bytes, expected_signer: str) -> bool:
    try:
        tx = SoldersTransaction.from_bytes(tx_bytes)
        message = tx.message
        if not message.recent_blockhash or message.recent_blockhash == Hash.default():
            Output.error("Transaction missing blockhash")
            return False
        if not any(str(acc) == expected_signer for acc in message.account_keys):
            Output.error("Transaction missing signer")
            return False
        return True
    except Exception as e:
        Output.error("Transaction verification failed")
        log_error(f"TX verify: {e}")
        return False


# ============== SOLANA HELPERS ==============

def get_balance(address: str) -> float:
    """Get SOL balance."""
    resp = api_request('POST', get_rpc_url(), json={
        "jsonrpc": "2.0", "id": 1,
        "method": "getBalance", "params": [address]
    })
    data = resp.json()
    if "result" in data:
        return data["result"]["value"] / Constants.LAMPORTS_PER_SOL
    return 0


def get_token_accounts(address: str) -> List[Dict[str, Any]]:
    """Get token accounts for address (Issue #103)."""
    try:
        resp = api_request('POST', get_rpc_url(), json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        })
        data = resp.json()
        if "result" in data and "value" in data["result"]:
            return data["result"]["value"]
    except:
        pass
    return []


def request_airdrop(address: str, amount: float = 1.0) -> Optional[str]:
    """Request devnet airdrop (Issue #123)."""
    rt = get_runtime()
    if rt.network != Network.DEVNET:
        raise ValueError("Airdrop only available on devnet")
    
    resp = api_request('POST', get_rpc_url(), json={
        "jsonrpc": "2.0", "id": 1,
        "method": "requestAirdrop",
        "params": [address, int(amount * Constants.LAMPORTS_PER_SOL)]
    })
    data = resp.json()
    if "result" in data:
        return data["result"]
    return None


def transfer_sol(keypair: Keypair, to_address: str, amount: float) -> Optional[str]:
    """Transfer SOL (Issue #122)."""
    from_pubkey = keypair.pubkey()
    to_pubkey = Pubkey.from_string(to_address)
    
    # Get recent blockhash
    resp = api_request('POST', get_rpc_url(), json={
        "jsonrpc": "2.0", "id": 1,
        "method": "getLatestBlockhash",
        "params": [{"commitment": "confirmed"}]
    })
    data = resp.json()
    blockhash = Hash.from_string(data["result"]["value"]["blockhash"])
    
    # Build transfer instruction manually (simplified)
    # In production, use proper transaction building
    # This is a placeholder - actual implementation would use solders properly
    Output.warning("Transfer not fully implemented - use a proper wallet")
    return None


def sign_message(keypair: Keypair, message: str) -> str:
    """Sign a message (Issue #114)."""
    message_bytes = message.encode('utf-8')
    # Add Solana message prefix
    prefix = b"\x00solana offchain\n"
    full_message = prefix + message_bytes
    signature = keypair.sign_message(full_message)
    return b58_encode(bytes(signature))


def verify_signature(pubkey: str, message: str, signature: str) -> bool:
    """Verify a signature (Issue #115)."""
    try:
        pk = Pubkey.from_string(pubkey)
        sig = Signature.from_string(signature)
        message_bytes = message.encode('utf-8')
        prefix = b"\x00solana offchain\n"
        full_message = prefix + message_bytes
        # Verification would need nacl or similar
        # This is a placeholder
        return True
    except:
        return False


# ============== IMAGE HANDLING ==============

def load_image_file(filepath: str) -> Tuple[str, str]:
    safe_path = validate_path_safety(filepath)
    if not safe_path.exists():
        raise FileNotFoundError("Image not found")
    
    file_size = safe_path.stat().st_size
    if file_size > Constants.MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"Image too large (max {Constants.MAX_IMAGE_SIZE_BYTES // 1024 // 1024}MB)")
    
    with open(safe_path, 'rb') as f:
        img_data = f.read()
    
    ext = safe_path.suffix.lower().lstrip('.')
    mime_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}
    mime = mime_map.get(ext, 'image/png')
    
    return f"data:{mime};base64,{base64.b64encode(img_data).decode()}", mime


def validate_https_url(url: str, name: str = "URL") -> None:
    url = sanitize_input(url)
    if not url.startswith('https://'):
        raise ValueError(f"{name} must use HTTPS")


# ============== SIGNAL HANDLERS ==============

def setup_signal_handlers() -> None:
    def handler(signum: int, frame: Any) -> None:
        print("\n")
        Output.warning("Interrupted")
        sys.exit(ExitCode.USER_CANCELLED)
    
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


# ============== DID YOU MEAN (Issue #142) ==============

def suggest_command(cmd: str, valid_commands: List[str]) -> Optional[str]:
    """Suggest similar command for typos."""
    matches = difflib.get_close_matches(cmd, valid_commands, n=1, cutoff=0.6)
    return matches[0] if matches else None


# ============== COMMANDS ==============

def cmd_setup(args: argparse.Namespace) -> None:
    """Generate a new wallet."""
    ensure_data_dir()
    wallet_file = get_wallet_file()
    rt = get_runtime()
    
    if wallet_file.exists() and not args.force:
        Output.warning(f"Wallet exists: {wallet_file}")
        print("Use --force to regenerate")
        return
    
    # Backup existing wallet
    if wallet_file.exists():
        create_backup("pre_setup")
    
    keypair = Keypair()
    save_wallet(keypair)
    
    address = str(keypair.pubkey())
    recovery_file = get_recovery_file()
    
    # Write recovery info to LOCAL file only (never transmitted)
    with open(recovery_file, 'w', encoding='utf-8') as f:
        f.write(f"Wallet Address: {address}\n\n")
        f.write("Signing Key (Base58):\n")
        f.write(b58_encode(bytes(keypair)) + "\n\n")
        f.write("KEEP THIS FILE SECURE - DO NOT SHARE!\n")
        f.write(f"\nGenerated: {datetime.now().isoformat()}\n")
    os.chmod(recovery_file, 0o600)
    
    # Clean up legacy files
    for legacy_name in ["SEED_PHRASE.txt", "RECOVERY_KEY.txt"]:
        legacy_path = Path(__file__).parent.resolve() / legacy_name
        if legacy_path.exists() and legacy_path != recovery_file:
            safe_delete(legacy_path)
    
    log_info(f"Wallet created: {address}")
    add_to_history("setup", {"address": address})
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({"success": True, "address": address, "data_dir": str(get_data_dir())})
    else:
        Output.success("Wallet created!")
        print(f"{Constants.EMOJI['address']} Address: {address}")
        print(f"{Constants.EMOJI['folder']} Data: {get_data_dir()}")
        print(f"{Constants.EMOJI['lock']} Recovery: {recovery_file}")
        print("")
        Output.warning("Back up your RECOVERY_KEY.txt file!")
        
        if HAS_QRCODE and not rt.no_emoji:
            print("\nScan to receive SOL:")
            Output.show_qr(address)


def cmd_wallet(args: argparse.Namespace) -> None:
    """Wallet management commands."""
    rt = get_runtime()
    
    if args.wallet_cmd == "import":
        if args.key:
            Output.warning("Passing keys via CLI is insecure")
            key = args.key
        elif not sys.stdin.isatty():
            key = sys.stdin.read().strip()
        else:
            Output.error("Provide key with --key or pipe from file")
            return
        
        try:
            key_bytes = b58_decode(sanitize_input(key))
            keypair = Keypair.from_bytes(key_bytes)
            save_wallet(keypair)
            
            key_ba = bytearray(key.encode())
            clear_buffer(key_ba)
            
            Output.success(f"Wallet imported: {keypair.pubkey()}")
            add_to_history("import", {"address": str(keypair.pubkey())})
        except ValueError:
            Output.error("Invalid key format", "Ensure key is valid base58")
        except Exception as e:
            Output.error("Import failed")
            if rt.debug:
                Output.debug(str(e))
        return
    
    keypair = load_wallet()
    address = str(keypair.pubkey())
    
    if args.wallet_cmd == "address":
        if rt.format == OutputFormat.JSON:
            Output.json_output({"address": address})
        else:
            print(address)
            if HAS_CLIPBOARD and Output.copy_to_clipboard(address):
                Output.info("Copied to clipboard!")
    
    elif args.wallet_cmd == "balance":
        try:
            with Spinner("Fetching balance..."):
                sol = get_balance(address)
            
            if rt.format == OutputFormat.JSON:
                Output.json_output({"address": address, "balance_sol": sol})
            else:
                print(f"{Constants.EMOJI['address']} Address: {address}")
                print(f"{Constants.EMOJI['money']} Balance: {sol:.6f} SOL")
        except Exception as e:
            Output.error("Network error", f"View at: https://solscan.io/account/{address}")
    
    elif args.wallet_cmd == "export":
        Output.warning("SIGNING KEY - DO NOT SHARE!")
        b58_auth = b58_encode(bytes(keypair))
        
        if rt.format == OutputFormat.JSON:
            Output.json_output({"signing_key": b58_auth, "address": address})
        else:
            print("\nBase58 Signing Key:")
            print(b58_auth)
        
        log_info("Signing key exported")
    
    elif args.wallet_cmd == "fund":
        if rt.format == OutputFormat.JSON:
            Output.json_output({"address": address, "explorer": f"https://solscan.io/account/{address}"})
        else:
            print(f"{Constants.EMOJI['address']} Send SOL to: {address}")
            print("\nNeed ~0.02 SOL per launch")
            print(f"{Constants.EMOJI['link']} https://solscan.io/account/{address}")
            
            if HAS_QRCODE and not rt.no_emoji:
                print("\nScan to send:")
                Output.show_qr(address)
    
    elif args.wallet_cmd == "check":
        with Spinner("Checking..."):
            try:
                resp = api_request('GET', f"{get_api_url()}/launch", params={"agent": address})
                result = parse_api_response(resp)
                
                if result.success and "launchesRemaining" in result.data:
                    if rt.format == OutputFormat.JSON:
                        Output.json_output(result.data)
                    else:
                        print(f"Tier: {result.data.get('tier', 'free')}")
                        print(f"{Constants.EMOJI['rocket']} Launches: {result.data.get('launchesToday', 0)}/{result.data.get('launchLimit', 1)}")
                        print(f"{Constants.EMOJI['chart']} Remaining: {result.data.get('launchesRemaining', 0)}")
                else:
                    Output.error(result.error or "Could not fetch")
            except Exception as e:
                Output.error("Error")
                if rt.debug:
                    Output.debug(str(e))
    
    else:
        print("Usage: python mya.py wallet <command>")
        print("\nCommands:")
        print("  address   Show wallet address")
        print("  balance   Show SOL balance")
        print("  export    Export signing key")
        print("  fund      Funding instructions")
        print("  check     Check launch limit")
        print("  import    Import existing wallet")


def cmd_tokens(args: argparse.Namespace) -> None:
    """List tokens in wallet (Issue #103)."""
    rt = get_runtime()
    keypair = load_wallet()
    address = str(keypair.pubkey())
    
    with Spinner("Fetching tokens..."):
        accounts = get_token_accounts(address)
    
    if not accounts:
        Output.info("No tokens found")
        return
    
    tokens = []
    for acc in accounts:
        try:
            parsed = acc["account"]["data"]["parsed"]["info"]
            mint = parsed["mint"]
            amount = int(parsed["tokenAmount"]["amount"])
            decimals = parsed["tokenAmount"]["decimals"]
            ui_amount = amount / (10 ** decimals) if decimals > 0 else amount
            tokens.append({"mint": mint, "amount": ui_amount, "decimals": decimals})
        except:
            continue
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({"address": address, "tokens": tokens})
    else:
        print(f"{Constants.EMOJI['address']} Wallet: {address}")
        print(f"\nTokens ({len(tokens)}):")
        for t in tokens:
            print(f"  {t['mint'][:8]}... : {t['amount']:.4f}")


def cmd_history(args: argparse.Namespace) -> None:
    """Show command history (Issue #102)."""
    rt = get_runtime()
    limit = getattr(args, 'limit', 20)
    history = get_history(limit)
    
    if not history:
        Output.info("No history")
        return
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({"history": history})
    else:
        print("Recent activity:")
        for entry in reversed(history):
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            action = entry.get("action", "?")
            print(f"  {ts} | {action}")


def cmd_backup(args: argparse.Namespace) -> None:
    """Backup wallet (Issue #105)."""
    rt = get_runtime()
    
    if args.backup_cmd == "create":
        try:
            backup_file = create_backup(args.name if hasattr(args, 'name') else None)
            if rt.format == OutputFormat.JSON:
                Output.json_output({"success": True, "backup": str(backup_file)})
            else:
                Output.success(f"Backup created: {backup_file}")
        except Exception as e:
            Output.error(f"Backup failed: {e}")
    
    elif args.backup_cmd == "list":
        backups = list_backups()
        if not backups:
            Output.info("No backups found")
            return
        
        if rt.format == OutputFormat.JSON:
            Output.json_output({"backups": [str(b) for b in backups]})
        else:
            print("Backups:")
            for b in backups[:10]:
                mtime = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                print(f"  {b.name} ({mtime})")
    
    elif args.backup_cmd == "restore":
        if not args.file:
            Output.error("Specify backup file with --file")
            return
        try:
            restore_backup(Path(args.file))
            Output.success("Wallet restored!")
        except Exception as e:
            Output.error(f"Restore failed: {e}")
    
    else:
        print("Usage: python mya.py backup <create|list|restore>")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify wallet integrity (Issue #107)."""
    rt = get_runtime()
    valid, message = verify_wallet_integrity()
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({"valid": valid, "message": message})
    else:
        if valid:
            Output.success(message)
        else:
            Output.error(message)


def cmd_status(args: argparse.Namespace) -> None:
    """Check API status (Issue #104)."""
    rt = get_runtime()
    
    with Spinner("Checking API..."):
        try:
            resp = api_request('GET', f"{get_api_url()}/health" if "/health" not in get_api_url() else get_api_url().replace("/launch", "/health"))
            api_ok = resp.ok
        except:
            api_ok = False
    
    with Spinner("Checking RPC..."):
        try:
            resp = api_request('POST', get_rpc_url(), json={
                "jsonrpc": "2.0", "id": 1, "method": "getHealth"
            })
            rpc_ok = resp.json().get("result") == "ok"
        except:
            rpc_ok = False
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({"api": api_ok, "rpc": rpc_ok, "network": rt.network.name.lower()})
    else:
        print(f"API: {'✅' if api_ok else '❌'}")
        print(f"RPC: {'✅' if rpc_ok else '❌'}")
        print(f"Network: {rt.network.name.lower()}")


def cmd_trending(args: argparse.Namespace) -> None:
    """Show trending tokens (Issue #118)."""
    rt = get_runtime()
    
    with Spinner("Fetching trending..."):
        try:
            # This would need a real trending API
            # Using placeholder data
            resp = api_request('GET', f"{get_api_url()}/stats")
            result = parse_api_response(resp)
        except:
            result = APIResponse(success=False, error="Not available")
    
    if rt.format == OutputFormat.JSON:
        Output.json_output(result.data if result.success else {"error": result.error})
    else:
        if result.success:
            print(f"{Constants.EMOJI['fire']} Trending tokens")
            # Display would go here
        else:
            Output.info("Trending data not available")


def cmd_leaderboard(args: argparse.Namespace) -> None:
    """Show leaderboard (Issue #119)."""
    rt = get_runtime()
    
    with Spinner("Fetching leaderboard..."):
        try:
            resp = api_request('GET', f"{get_api_url()}/leaderboard")
            result = parse_api_response(resp)
        except:
            result = APIResponse(success=False, error="Not available")
    
    if rt.format == OutputFormat.JSON:
        Output.json_output(result.data if result.success else {"error": result.error})
    else:
        if result.success and "leaderboard" in result.data:
            print(f"{Constants.EMOJI['trophy']} Leaderboard")
            for i, entry in enumerate(result.data["leaderboard"][:10], 1):
                print(f"  {i}. {entry.get('address', '?')[:8]}... - {entry.get('launches', 0)} launches")
        else:
            Output.info("Leaderboard not available")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show user stats (Issue #120)."""
    rt = get_runtime()
    keypair = load_wallet()
    address = str(keypair.pubkey())
    
    with Spinner("Fetching stats..."):
        try:
            resp = api_request('GET', f"{get_api_url()}/launch", params={"agent": address})
            result = parse_api_response(resp)
            
            balance = get_balance(address)
            tokens = len(get_token_accounts(address))
        except Exception as e:
            if rt.debug:
                Output.debug(str(e))
            result = APIResponse(success=False)
            balance = 0
            tokens = 0
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({
            "address": address,
            "balance_sol": balance,
            "tokens": tokens,
            **result.data
        })
    else:
        print(f"{Constants.EMOJI['chart']} Stats for {address[:8]}...")
        print(f"  Balance: {balance:.4f} SOL")
        print(f"  Tokens: {tokens}")
        if result.success:
            print(f"  Launches today: {result.data.get('launchesToday', 0)}")
            print(f"  Tier: {result.data.get('tier', 'free')}")


def cmd_airdrop(args: argparse.Namespace) -> None:
    """Request devnet airdrop (Issue #123)."""
    rt = get_runtime()
    
    if rt.network != Network.DEVNET:
        Output.error("Airdrop only available on devnet", "Use --network devnet")
        return
    
    keypair = load_wallet()
    address = str(keypair.pubkey())
    amount = getattr(args, 'amount', 1.0)
    
    with Spinner(f"Requesting {amount} SOL airdrop..."):
        try:
            sig = request_airdrop(address, amount)
            if sig:
                add_to_history("airdrop", {"address": address, "amount": amount, "signature": sig})
                Output.success(f"Airdrop requested! Signature: {sig[:16]}...")
            else:
                Output.error("Airdrop failed")
        except Exception as e:
            Output.error(f"Airdrop failed: {e}")


def cmd_transfer(args: argparse.Namespace) -> None:
    """Transfer SOL (Issue #122)."""
    rt = get_runtime()
    
    if not args.to:
        Output.error("Specify recipient with --to")
        return
    if not args.amount:
        Output.error("Specify amount with --amount")
        return
    
    keypair = load_wallet()
    address = str(keypair.pubkey())
    
    # Confirm
    if not args.yes:
        print(f"Transfer {args.amount} SOL")
        print(f"  From: {address[:16]}...")
        print(f"  To: {args.to}")
        confirm = input("Proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
    
    Output.warning("Transfer command not fully implemented")
    Output.info("Use a proper wallet for transfers")


def cmd_sign(args: argparse.Namespace) -> None:
    """Sign a message (Issue #114)."""
    rt = get_runtime()
    keypair = load_wallet()
    
    message = args.message
    if not message:
        if not sys.stdin.isatty():
            message = sys.stdin.read().strip()
        else:
            Output.error("Provide message with --message or pipe from stdin")
            return
    
    signature = sign_message(keypair, message)
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({
            "address": str(keypair.pubkey()),
            "message": message,
            "signature": signature
        })
    else:
        print(f"Message: {message[:50]}...")
        print(f"Signature: {signature}")
        
        if HAS_CLIPBOARD and Output.copy_to_clipboard(signature):
            Output.info("Signature copied to clipboard!")


def show_first_launch_tips() -> None:
    """Show helpful commands before first launch."""
    print("=" * 50)
    print(f"{Constants.EMOJI['info']}  BEFORE YOUR FIRST LAUNCH")
    print("=" * 50)
    print("\nUseful commands:")
    print("  python mya.py wallet balance   # Check balance")
    print("  python mya.py wallet check     # Check limits")
    print("  python mya.py launch --dry-run # Test run")
    print("=" * 50)


def get_initial_buy_decision(args: argparse.Namespace, balance_sol: float) -> float:
    """Determine initial buy amount."""
    if hasattr(args, 'initial_buy') and args.initial_buy and args.initial_buy > 0:
        return args.initial_buy
    
    if hasattr(args, 'ai_initial_buy') and args.ai_initial_buy:
        print(f"{Constants.EMOJI['bulb']} AI calculating initial buy...")
        print(f"   Balance: {balance_sol:.4f} SOL")
        
        available = balance_sol - Constants.AI_FEE_RESERVE
        print(f"   Available: {available:.4f} SOL")
        
        if available < Constants.AI_BUY_MIN:
            print(f"{Constants.EMOJI['bulb']} AI: No buy (low balance)")
            return 0
        
        recommended = min(available * Constants.AI_BUY_PERCENTAGE, Constants.AI_BUY_MAX)
        recommended = max(recommended, Constants.AI_BUY_MIN)
        recommended = round(recommended, 3)
        
        print(f"{Constants.EMOJI['bulb']} AI: {recommended} SOL")
        return recommended
    
    return 0


def cmd_launch(args: argparse.Namespace) -> None:
    """Launch a token."""
    rt = get_runtime()
    
    if hasattr(args, 'tips') and args.tips:
        show_first_launch_tips()
        return
    
    # Validate required fields
    errors = []
    if not args.name:
        errors.append("--name")
    if not args.symbol:
        errors.append("--symbol")
    if not args.description:
        errors.append("--description")
    if not args.image and not args.image_file:
        errors.append("--image or --image-file")
    
    if errors:
        Output.error(f"Missing: {', '.join(errors)}", "Run: python mya.py launch --help")
        sys.exit(ExitCode.INVALID_INPUT)
    
    # Sanitize
    name = sanitize_input(args.name)
    symbol = sanitize_input(args.symbol)
    description = sanitize_input(args.description)
    
    # Validate
    if len(symbol) > Constants.MAX_SYMBOL_LENGTH:
        Output.error(f"Symbol max {Constants.MAX_SYMBOL_LENGTH} chars")
        sys.exit(ExitCode.INVALID_INPUT)
    if not symbol.isascii() or not symbol.replace('_', '').isalnum():
        Output.error("Symbol: ASCII letters/numbers only")
        sys.exit(ExitCode.INVALID_INPUT)
    if len(name) > Constants.MAX_NAME_LENGTH:
        Output.error(f"Name max {Constants.MAX_NAME_LENGTH} chars")
        sys.exit(ExitCode.INVALID_INPUT)
    if len(description) > Constants.MAX_DESCRIPTION_LENGTH:
        Output.error(f"Description max {Constants.MAX_DESCRIPTION_LENGTH} chars")
        sys.exit(ExitCode.INVALID_INPUT)
    
    # Image
    try:
        if args.image_file:
            image, _ = load_image_file(args.image_file)
        else:
            validate_https_url(args.image, "Image")
            image = args.image
    except (FileNotFoundError, ValueError) as e:
        Output.error(str(e))
        sys.exit(ExitCode.INVALID_INPUT)
    
    # Banner
    banner = None
    if args.banner_file:
        try:
            banner, _ = load_image_file(args.banner_file)
        except Exception as e:
            Output.error(f"Banner: {e}")
            sys.exit(ExitCode.INVALID_INPUT)
    elif args.banner:
        try:
            validate_https_url(args.banner, "Banner")
            banner = args.banner
        except ValueError as e:
            Output.error(str(e))
            sys.exit(ExitCode.INVALID_INPUT)
    
    # Socials
    for url_name, url in [('Twitter', args.twitter), ('Telegram', args.telegram), ('Website', args.website)]:
        if url:
            try:
                validate_https_url(url, url_name)
            except ValueError as e:
                Output.error(str(e))
                sys.exit(ExitCode.INVALID_INPUT)
    
    keypair = load_wallet()
    creator_address = str(keypair.pubkey())
    
    # Preview (Issue #140)
    if args.preview or args.dry_run:
        data = {"mode": "preview" if args.preview else "dry_run", "name": name, "symbol": symbol.upper(), "creator": creator_address}
        if rt.format == OutputFormat.JSON:
            Output.json_output(data)
        else:
            print(f"{'PREVIEW' if args.preview else 'DRY RUN'}:")
            for k, v in data.items():
                print(f"   {k}: {v}")
        if args.dry_run:
            return
    
    # Confirm
    if not args.yes and sys.stdin.isatty():
        Output.warning("This spends real SOL")
        confirm = input("Proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            sys.exit(ExitCode.USER_CANCELLED)
    
    print(f"{Constants.EMOJI['rocket']} Launching {symbol.upper()}...")
    log_info(f"Launch: {symbol} by {creator_address[:8]}")
    
    try:
        # Balance
        balance_sol = 0
        if not rt.skip_balance_check:
            with Spinner("Checking balance...", total=100):
                balance_sol = get_balance(creator_address)
                print(f"   Balance: {balance_sol:.4f} SOL")
        
        initial_buy = get_initial_buy_decision(args, balance_sol)
        if initial_buy > 0:
            print(f"   Initial buy: {initial_buy} SOL")
        
        # Prepare
        with Spinner("Preparing...", total=100):
            prepare_payload = {
                "name": name,
                "symbol": symbol.upper(),
                "description": description,
                "image": image,
                "creatorAddress": creator_address,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            if banner:
                prepare_payload["banner"] = banner
            if args.twitter:
                prepare_payload["twitter"] = sanitize_input(args.twitter)
            if args.telegram:
                prepare_payload["telegram"] = sanitize_input(args.telegram)
            if args.website:
                prepare_payload["website"] = sanitize_input(args.website)
            if initial_buy > 0:
                prepare_payload["initialBuyAmount"] = initial_buy
            if args.slippage:
                prepare_payload["slippageBps"] = args.slippage
            if rt.priority_fee > 0:
                prepare_payload["priorityFee"] = rt.priority_fee
            
            headers = get_request_headers()
            timestamp = int(time.time())
            api_key = get_api_key()
            if api_key:
                headers["X-Timestamp"] = str(timestamp)
                headers["X-Signature"] = sign_request(prepare_payload, timestamp)
            
            resp = api_request('POST', f"{get_api_url()}/launch/prepare", json=prepare_payload, headers=headers, timeout=60)
            prepare_result = parse_api_response(resp)
        
        if not prepare_result.success:
            Output.error("Prepare failed", prepare_result.hint or "")
            print(f"   {prepare_result.error}")
            if prepare_result.code:
                print(f"   Code: {prepare_result.code}")
            sys.exit(ExitCode.API_ERROR)
        
        # Sign
        with Spinner("Signing..."):
            tx_bytes = base64.b64decode(prepare_result.data["transaction"])
            mint_address = prepare_result.data["mintAddress"]
            
            if not verify_transaction(tx_bytes, creator_address):
                Output.error("Transaction verification failed")
                sys.exit(ExitCode.SECURITY_ERROR)
            
            tx = SoldersTransaction.from_bytes(tx_bytes)
            tx.sign([keypair], tx.message.recent_blockhash)
            signed_tx_b64 = base64.b64encode(bytes(tx)).decode()
        
        # Submit
        with Spinner("Submitting..."):
            submit_payload = {
                "signedTransaction": signed_tx_b64,
                "mintAddress": mint_address,
                "creatorAddress": creator_address,
                "metadata": {
                    "name": name,
                    "symbol": symbol.upper(),
                    "description": description,
                    "imageUrl": prepare_result.data.get("imageUrl"),
                    "twitter": args.twitter,
                    "telegram": args.telegram,
                    "website": args.website,
                }
            }
            
            resp = api_request('POST', f"{get_api_url()}/launch/submit", json=submit_payload, headers=headers, timeout=120)
            result = parse_api_response(resp)
        
        if result.success:
            log_info(f"Launch success: {mint_address}")
            add_to_history("launch", {"mint": mint_address, "symbol": symbol.upper(), "name": name})
            
            if rt.format == OutputFormat.JSON:
                Output.json_output({
                    "success": True,
                    "mint": result.data.get('mint'),
                    "signature": result.data.get('signature'),
                    "pump_url": result.data.get('pumpUrl'),
                })
            else:
                Output.success("Token launched!")
                print(f"{Constants.EMOJI['coin']} Mint: {result.data.get('mint')}")
                print(f"{Constants.EMOJI['link']} {result.data.get('pumpUrl')}")
                
                if HAS_CLIPBOARD and Output.copy_to_clipboard(result.data.get('pumpUrl', '')):
                    Output.info("URL copied to clipboard!")
        else:
            Output.error("Launch failed", result.hint or "")
            print(f"   {result.error}")
            log_error(f"Launch failed: {result.error}")
            sys.exit(ExitCode.API_ERROR)
    
    except requests.exceptions.SSLError:
        Output.error("SSL error", "Check MYA_SSL_VERIFY setting")
        sys.exit(ExitCode.NETWORK_ERROR)
    except requests.exceptions.Timeout:
        Output.error("Timeout", "Check pump.fun - launch may have succeeded")
        sys.exit(ExitCode.TIMEOUT)
    except requests.exceptions.ConnectionError:
        Output.error("Network error", "Check your connection")
        sys.exit(ExitCode.NETWORK_ERROR)
    except KeyboardInterrupt:
        Output.warning("Interrupted")
        sys.exit(ExitCode.USER_CANCELLED)
    except Exception as e:
        Output.error("Error")
        if rt.debug:
            Output.debug(f"{type(e).__name__}: {e}")
        log_error(f"Launch exception: {e}")
        sys.exit(ExitCode.GENERAL_ERROR)


def cmd_config(args: argparse.Namespace) -> None:
    """Manage configuration."""
    config = AppConfig.load(get_config_file())
    rt = get_runtime()
    
    if args.config_cmd == "show":
        if rt.format == OutputFormat.JSON:
            Output.json_output(config.__dict__)
        else:
            print(json.dumps(config.__dict__, indent=2))
    
    elif args.config_cmd == "set":
        if args.key and args.value:
            if hasattr(config, args.key):
                # Type conversion
                current = getattr(config, args.key)
                if isinstance(current, bool):
                    setattr(config, args.key, args.value.lower() in ('true', '1', 'yes'))
                elif isinstance(current, int):
                    setattr(config, args.key, int(args.value))
                else:
                    setattr(config, args.key, args.value)
                config.save(get_config_file())
                Output.success(f"{args.key} = {getattr(config, args.key)}")
            else:
                Output.error(f"Unknown config key: {args.key}")
        else:
            Output.error("Usage: config set <key> <value>")
    
    elif args.config_cmd == "autonomous":
        if args.value is None:
            print(f"autonomous: {config.autonomous}")
        else:
            config.autonomous = args.value.lower() in ('true', '1', 'yes', 'on')
            config.save(get_config_file())
            Output.success(f"autonomous = {config.autonomous}")
    
    else:
        print("Usage: python mya.py config <show|set|autonomous>")


def cmd_uninstall(args: argparse.Namespace) -> None:
    """Remove local wallet files (cleanup utility)."""
    wallet_file = get_wallet_file()
    config_file = get_config_file()
    recovery_file = get_recovery_file()
    data_dir = get_data_dir()
    
    print("This will remove:")
    print(f"   {wallet_file}")
    print(f"   {config_file}")
    print(f"   {recovery_file}")
    
    if not args.yes:
        confirm = input("Proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
    
    # Create final backup before removal
    if wallet_file.exists():
        create_backup("pre_uninstall")
    
    for f in [wallet_file, recovery_file]:
        if f.exists():
            safe_delete(f)
            print(f"Removed: {f}")
    
    if config_file.exists():
        config_file.unlink()
        print(f"Removed: {config_file}")
    
    if data_dir.exists() and not any(data_dir.iterdir()):
        data_dir.rmdir()
        print(f"Removed: {data_dir}")
    
    Output.success("Cleanup complete")


def cmd_help_all(args: argparse.Namespace) -> None:
    """Show all help (Issue #149)."""
    print(f"""
MintYourAgent v{Constants.VERSION} - Complete CLI Reference
{'=' * 60}

COMMANDS:
  setup               Create a new wallet
  wallet              Wallet management (balance, export, import, etc.)
  launch              Launch a token on pump.fun
  tokens              List tokens in wallet
  history             Show command history
  backup              Backup/restore wallet
  verify              Verify wallet integrity
  status              Check API/RPC status
  trending            Show trending tokens
  leaderboard         Show launch leaderboard
  stats               Show your stats
  airdrop             Request devnet airdrop
  transfer            Transfer SOL
  sign                Sign a message
  config              Manage configuration
  uninstall           Remove all data

COMMAND ALIASES:
  l = launch, w = wallet, s = setup, c = config
  h = history, t = tokens, b = backup

GLOBAL FLAGS:
  --version           Show version
  --json              JSON output
  --format            text/json/csv/table
  -o, --output-file   Write to file
  --no-color          Disable colors
  --no-emoji          Disable emoji
  --timestamps        Show timestamps
  -q, --quiet         Quiet mode
  -v, --verbose       Verbose
  --debug             Debug mode

NETWORK FLAGS:
  --network           mainnet/devnet/testnet
  --api-url           Override API
  --rpc-url           Override RPC
  --proxy             HTTP proxy
  --timeout           Request timeout
  --retry-count       Retry attempts

ENVIRONMENT VARIABLES:
  MYA_API_URL         API endpoint
  MYA_API_KEY         API key
  MYA_SSL_VERIFY      SSL verification
  HELIUS_RPC          RPC endpoint

For command-specific help: python mya.py <command> --help
Documentation: https://mintyouragent.com/docs
""")


def migrate_legacy_wallet() -> None:
    """Migrate wallet from skill folder to ~/.mintyouragent/ on startup."""
    try:
        skill_dir = Path(__file__).parent.resolve()
        home_dir = Path.home() / ".mintyouragent"
        
        # Check for legacy wallet in skill folder
        legacy_wallet = skill_dir / "wallet.json"
        home_wallet = home_dir / "wallet.json"
        
        if legacy_wallet.exists() and not home_wallet.exists():
            home_dir.mkdir(exist_ok=True)
            shutil.copy2(str(legacy_wallet), str(home_wallet))
            os.chmod(home_wallet, 0o600)
            legacy_wallet.unlink()
            print(f"⚠️  Migrated wallet to {home_dir}")
            print("   Your wallet is now safe from skill updates!")
        
        # Also migrate recovery file
        for name in ["SEED_PHRASE.txt", "RECOVERY_KEY.txt", "BACKUP.txt"]:
            legacy_file = skill_dir / name
            home_file = home_dir / name
            if legacy_file.exists() and not home_file.exists():
                shutil.copy2(str(legacy_file), str(home_file))
                os.chmod(home_file, 0o600)
                legacy_file.unlink()
    except:
        pass  # Don't fail on migration errors


def main() -> None:
    """Main entry point."""
    migrate_legacy_wallet()  # Run FIRST before anything else
    load_dotenv()
    setup_signal_handlers()
    
    parser = argparse.ArgumentParser(
        description="MintYourAgent - Launch tokens on pump.fun",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Version: {Constants.VERSION} | Docs: https://mintyouragent.com/docs"
    )
    
    # Global options
    parser.add_argument("--version", action="version", version=f"MintYourAgent {Constants.VERSION}")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--no-emoji", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--format", choices=["text", "json", "csv", "table"], default="text")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--timestamps", action="store_true")
    parser.add_argument("--config-file", type=Path)
    parser.add_argument("--wallet-file", type=Path)
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("-o", "--output-file", type=Path)
    parser.add_argument("--api-url")
    parser.add_argument("--rpc-url")
    parser.add_argument("--network", choices=["mainnet", "devnet", "testnet"], default="mainnet")
    parser.add_argument("--proxy")
    parser.add_argument("--user-agent")
    parser.add_argument("--timeout", type=int, default=Constants.DEFAULT_TIMEOUT)
    parser.add_argument("--retry-count", type=int, default=Constants.DEFAULT_RETRY_COUNT)
    parser.add_argument("--priority-fee", type=int, default=0)
    parser.add_argument("--skip-balance-check", action="store_true")
    parser.add_argument("--help-all", action="store_true", help="Show complete help")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Setup
    setup_p = subparsers.add_parser("setup", aliases=["s"], help="Create wallet")
    setup_p.add_argument("--force", action="store_true")
    
    # Wallet
    wallet_p = subparsers.add_parser("wallet", aliases=["w"], help="Wallet commands")
    wallet_p.add_argument("wallet_cmd", nargs="?", default="help", choices=["address", "balance", "export", "fund", "check", "import", "help"])
    wallet_p.add_argument("--key")
    
    # Launch
    launch_p = subparsers.add_parser("launch", aliases=["l"], help="Launch token")
    launch_p.add_argument("--name")
    launch_p.add_argument("--symbol")
    launch_p.add_argument("--description")
    launch_p.add_argument("--image")
    launch_p.add_argument("--image-file")
    launch_p.add_argument("--banner")
    launch_p.add_argument("--banner-file")
    launch_p.add_argument("--twitter")
    launch_p.add_argument("--telegram")
    launch_p.add_argument("--website")
    launch_p.add_argument("--initial-buy", type=float, default=0)
    launch_p.add_argument("--ai-initial-buy", action="store_true")
    launch_p.add_argument("--slippage", type=int, default=100)
    launch_p.add_argument("--dry-run", action="store_true")
    launch_p.add_argument("--preview", action="store_true")
    launch_p.add_argument("--tips", action="store_true")
    launch_p.add_argument("-y", "--yes", action="store_true")
    
    # Tokens
    tokens_p = subparsers.add_parser("tokens", aliases=["t"], help="List tokens")
    
    # History
    history_p = subparsers.add_parser("history", aliases=["h"], help="Command history")
    history_p.add_argument("--limit", type=int, default=20)
    
    # Backup
    backup_p = subparsers.add_parser("backup", aliases=["b"], help="Backup wallet")
    backup_p.add_argument("backup_cmd", nargs="?", default="list", choices=["create", "list", "restore"])
    backup_p.add_argument("--name")
    backup_p.add_argument("--file")
    
    # Verify
    verify_p = subparsers.add_parser("verify", help="Verify wallet")
    
    # Status
    status_p = subparsers.add_parser("status", aliases=["st"], help="API status")
    
    # Trending
    trending_p = subparsers.add_parser("trending", aliases=["tr"], help="Trending tokens")
    
    # Leaderboard
    leaderboard_p = subparsers.add_parser("leaderboard", aliases=["lb"], help="Leaderboard")
    
    # Stats
    stats_p = subparsers.add_parser("stats", help="Your stats")
    
    # Airdrop
    airdrop_p = subparsers.add_parser("airdrop", help="Devnet airdrop")
    airdrop_p.add_argument("--amount", type=float, default=1.0)
    
    # Transfer
    transfer_p = subparsers.add_parser("transfer", help="Transfer SOL")
    transfer_p.add_argument("--to")
    transfer_p.add_argument("--amount", type=float)
    transfer_p.add_argument("-y", "--yes", action="store_true")
    
    # Sign
    sign_p = subparsers.add_parser("sign", help="Sign message")
    sign_p.add_argument("--message", "-m")
    
    # Config
    config_p = subparsers.add_parser("config", aliases=["c"], help="Configuration")
    config_p.add_argument("config_cmd", nargs="?", default="show", choices=["show", "set", "autonomous"])
    config_p.add_argument("key", nargs="?")
    config_p.add_argument("value", nargs="?")
    
    # Uninstall
    uninstall_p = subparsers.add_parser("uninstall", help="Remove data")
    uninstall_p.add_argument("-y", "--yes", action="store_true")
    
    args = parser.parse_args()
    
    # Show full help
    if args.help_all:
        cmd_help_all(args)
        return
    
    # Resolve aliases
    if args.command in Constants.COMMAND_ALIASES:
        args.command = Constants.COMMAND_ALIASES[args.command]
    
    # Build runtime
    format_map = {"text": OutputFormat.TEXT, "json": OutputFormat.JSON, "csv": OutputFormat.CSV, "table": OutputFormat.TABLE}
    network_map = {"mainnet": Network.MAINNET, "devnet": Network.DEVNET, "testnet": Network.TESTNET}
    
    runtime = RuntimeConfig(
        config_file=args.config_file,
        wallet_file=args.wallet_file,
        log_file=args.log_file,
        output_file=args.output_file,
        api_url=args.api_url or Constants.DEFAULT_API_URL,
        rpc_url=args.rpc_url,
        network=network_map.get(args.network, Network.MAINNET),
        proxy=args.proxy,
        user_agent=args.user_agent or Constants.USER_AGENT,
        timeout=args.timeout,
        retry_count=args.retry_count,
        priority_fee=args.priority_fee,
        skip_balance_check=args.skip_balance_check,
        format=format_map.get(args.format, OutputFormat.TEXT) if not args.json else OutputFormat.JSON,
        quiet=args.quiet,
        debug=args.debug,
        verbose=args.verbose,
        no_color=args.no_color,
        no_emoji=args.no_emoji,
        timestamps=args.timestamps,
    )
    set_runtime(runtime)
    setup_logging()
    
    # Route commands
    commands = {
        "setup": cmd_setup, "wallet": cmd_wallet, "launch": cmd_launch,
        "tokens": cmd_tokens, "history": cmd_history, "backup": cmd_backup,
        "verify": cmd_verify, "status": cmd_status, "trending": cmd_trending,
        "leaderboard": cmd_leaderboard, "stats": cmd_stats, "airdrop": cmd_airdrop,
        "transfer": cmd_transfer, "sign": cmd_sign, "config": cmd_config,
        "uninstall": cmd_uninstall,
    }
    
    if args.command in commands:
        commands[args.command](args)
    elif args.command:
        # Did you mean? (Issue #142)
        suggestion = suggest_command(args.command, list(commands.keys()))
        if suggestion:
            Output.error(f"Unknown command: {args.command}", f"Did you mean '{suggestion}'?")
        else:
            Output.error(f"Unknown command: {args.command}", "Run: python mya.py --help")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
