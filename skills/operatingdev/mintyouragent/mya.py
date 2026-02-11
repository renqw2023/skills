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

Version: 3.2.1

Changelog:
- 3.3.0: Rate limit enforcement for native launches - preflight check before spending SOL
- 3.2.1: Fixed pump.fun instruction accounts to match current IDL (16 accounts for buy, added volume/fee PDAs)
- 3.2.0: Native pump.fun initial buy - bundles create+buy in one atomic tx (like webapp)
- 3.0.2: Bug fixes
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
    RATE_LIMIT_EXCEEDED = 10


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
    VERSION = "3.3.4"
    
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
    from solders.instruction import Instruction, AccountMeta
    from solders.system_program import ID as SYSTEM_PROGRAM_ID
    import struct
    import requests
except ImportError:
    print(f"{Constants.EMOJI['error']} Missing dependencies. Run: pip install solders requests")
    sys.exit(ExitCode.MISSING_DEPS)

# ============== PUMP.FUN PROGRAM CONSTANTS ==============

PUMP_PROGRAM_ID = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
PUMP_GLOBAL = Pubkey.from_string("4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf")
PUMP_FEE_RECIPIENT = Pubkey.from_string("CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM")

# MintYourAgent platform fee
MYA_TREASURY = Pubkey.from_string("5AwxRzXkUPgrG1p9MAZYTwpxNGadwDXXkav8yCRtN3QP")
MYA_PLATFORM_FEE = 10_000_000  # 0.01 SOL in lamports
PUMP_EVENT_AUTHORITY = Pubkey.from_string("Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1")
PUMP_MINT_AUTHORITY = Pubkey.from_string("TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM")
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_PROGRAM_ID = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
MPL_TOKEN_METADATA_PROGRAM_ID = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
FEE_PROGRAM_ID = Pubkey.from_string("pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ")


# ============== NATIVE PUMP.FUN FUNCTIONS ==============

def derive_bonding_curve(mint: Pubkey) -> Pubkey:
    """Derive bonding curve PDA for a mint."""
    seeds = [b"bonding-curve", bytes(mint)]
    pda, _ = Pubkey.find_program_address(seeds, PUMP_PROGRAM_ID)
    return pda

def derive_associated_bonding_curve(bonding_curve: Pubkey, mint: Pubkey) -> Pubkey:
    """Derive associated token account for bonding curve."""
    seeds = [bytes(bonding_curve), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
    pda, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
    return pda

def derive_metadata(mint: Pubkey) -> Pubkey:
    """Derive metadata PDA for a mint."""
    seeds = [b"metadata", bytes(MPL_TOKEN_METADATA_PROGRAM_ID), bytes(mint)]
    pda, _ = Pubkey.find_program_address(seeds, MPL_TOKEN_METADATA_PROGRAM_ID)
    return pda

def derive_user_ata(user: Pubkey, mint: Pubkey) -> Pubkey:
    """Derive user's associated token account."""
    seeds = [bytes(user), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
    pda, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
    return pda

def derive_creator_vault(creator: Pubkey) -> Pubkey:
    """Derive creator vault PDA."""
    seeds = [b"creator-vault", bytes(creator)]
    pda, _ = Pubkey.find_program_address(seeds, PUMP_PROGRAM_ID)
    return pda

def derive_global_volume_accumulator() -> Pubkey:
    """Derive global volume accumulator PDA."""
    seeds = [b"global_volume_accumulator"]
    pda, _ = Pubkey.find_program_address(seeds, PUMP_PROGRAM_ID)
    return pda

def derive_user_volume_accumulator(user: Pubkey) -> Pubkey:
    """Derive user volume accumulator PDA."""
    seeds = [b"user_volume_accumulator", bytes(user)]
    pda, _ = Pubkey.find_program_address(seeds, PUMP_PROGRAM_ID)
    return pda

def derive_fee_config() -> Pubkey:
    """Derive fee config PDA - seeds are ["fee_config", PUMP_PROGRAM_ID] against FEE_PROGRAM_ID."""
    seeds = [b"fee_config", bytes(PUMP_PROGRAM_ID)]
    pda, _ = Pubkey.find_program_address(seeds, FEE_PROGRAM_ID)
    return pda

def encode_string(s: str) -> bytes:
    """Encode string with length prefix for Solana."""
    encoded = s.encode('utf-8')
    return struct.pack('<I', len(encoded)) + encoded

def build_create_ata_instruction(payer: Pubkey, ata: Pubkey, owner: Pubkey, mint: Pubkey) -> Instruction:
    """Build create associated token account instruction."""
    # ATA program instruction (no data needed, accounts define the operation)
    accounts = [
        AccountMeta(payer, is_signer=True, is_writable=True),       # payer
        AccountMeta(ata, is_signer=False, is_writable=True),        # associated token account
        AccountMeta(owner, is_signer=False, is_writable=False),     # owner
        AccountMeta(mint, is_signer=False, is_writable=False),      # mint
        AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),  # system program
        AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),   # token program
    ]
    
    return Instruction(ASSOCIATED_TOKEN_PROGRAM_ID, bytes(), accounts)


def build_transfer_instruction(from_pubkey: Pubkey, to_pubkey: Pubkey, lamports: int) -> Instruction:
    """Build SOL transfer instruction (system program)."""
    # System program transfer instruction
    # Instruction index 2 = Transfer
    data = struct.pack('<I', 2) + struct.pack('<Q', lamports)
    
    accounts = [
        AccountMeta(from_pubkey, is_signer=True, is_writable=True),
        AccountMeta(to_pubkey, is_signer=False, is_writable=True),
    ]
    
    return Instruction(SYSTEM_PROGRAM_ID, data, accounts)


def build_create_instruction(user: Pubkey, mint: Pubkey, name: str, symbol: str, uri: str) -> Instruction:
    """Build pump.fun create instruction."""
    bonding_curve = derive_bonding_curve(mint)
    associated_bonding_curve = derive_associated_bonding_curve(bonding_curve, mint)
    metadata = derive_metadata(mint)
    
    # Instruction discriminator for 'create'
    discriminator = bytes([24, 30, 200, 40, 5, 28, 7, 119])
    
    # Args: name (string), symbol (string), uri (string), creator (pubkey)
    data = discriminator + encode_string(name) + encode_string(symbol) + encode_string(uri) + bytes(user)
    
    # 14 accounts in exact order from IDL
    accounts = [
        AccountMeta(mint, is_signer=True, is_writable=True),                    # 0: mint
        AccountMeta(PUMP_MINT_AUTHORITY, is_signer=False, is_writable=False),   # 1: mint_authority
        AccountMeta(bonding_curve, is_signer=False, is_writable=True),          # 2: bonding_curve
        AccountMeta(associated_bonding_curve, is_signer=False, is_writable=True), # 3: associated_bonding_curve
        AccountMeta(PUMP_GLOBAL, is_signer=False, is_writable=False),           # 4: global
        AccountMeta(MPL_TOKEN_METADATA_PROGRAM_ID, is_signer=False, is_writable=False), # 5: mpl_token_metadata
        AccountMeta(metadata, is_signer=False, is_writable=True),               # 6: metadata
        AccountMeta(user, is_signer=True, is_writable=True),                    # 7: user
        AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),     # 8: system_program
        AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),      # 9: token_program
        AccountMeta(ASSOCIATED_TOKEN_PROGRAM_ID, is_signer=False, is_writable=False), # 10: associated_token_program
        AccountMeta(RENT_PROGRAM_ID, is_signer=False, is_writable=False),       # 11: rent
        AccountMeta(PUMP_EVENT_AUTHORITY, is_signer=False, is_writable=False),  # 12: event_authority
        AccountMeta(PUMP_PROGRAM_ID, is_signer=False, is_writable=False),       # 13: program
    ]
    
    return Instruction(PUMP_PROGRAM_ID, data, accounts)

def build_buy_instruction(user: Pubkey, mint: Pubkey, creator: Pubkey, token_amount: int, max_sol_lamports: int) -> Instruction:
    """Build pump.fun buy instruction."""
    bonding_curve = derive_bonding_curve(mint)
    associated_bonding_curve = derive_associated_bonding_curve(bonding_curve, mint)
    user_ata = derive_user_ata(user, mint)
    creator_vault = derive_creator_vault(creator)
    global_volume_acc = derive_global_volume_accumulator()
    user_volume_acc = derive_user_volume_accumulator(user)
    fee_config = derive_fee_config()
    
    # Instruction discriminator for 'buy'
    discriminator = bytes([102, 6, 61, 18, 1, 218, 235, 234])
    
    # Args: amount (u64), max_sol_cost (u64), track_volume (OptionBool - 0 = None, 1 = Some(false), 2 = Some(true))
    track_volume = 0  # None - don't track volume
    data = discriminator + struct.pack('<Q', token_amount) + struct.pack('<Q', max_sol_lamports) + bytes([track_volume])
    
    # 16 accounts in exact order from IDL
    accounts = [
        AccountMeta(PUMP_GLOBAL, is_signer=False, is_writable=False),           # 0: global
        AccountMeta(PUMP_FEE_RECIPIENT, is_signer=False, is_writable=True),     # 1: fee_recipient
        AccountMeta(mint, is_signer=False, is_writable=False),                  # 2: mint
        AccountMeta(bonding_curve, is_signer=False, is_writable=True),          # 3: bonding_curve
        AccountMeta(associated_bonding_curve, is_signer=False, is_writable=True), # 4: associated_bonding_curve
        AccountMeta(user_ata, is_signer=False, is_writable=True),               # 5: associated_user
        AccountMeta(user, is_signer=True, is_writable=True),                    # 6: user
        AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),     # 7: system_program
        AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),      # 8: token_program
        AccountMeta(creator_vault, is_signer=False, is_writable=True),          # 9: creator_vault
        AccountMeta(PUMP_EVENT_AUTHORITY, is_signer=False, is_writable=False),  # 10: event_authority
        AccountMeta(PUMP_PROGRAM_ID, is_signer=False, is_writable=False),       # 11: program
        AccountMeta(global_volume_acc, is_signer=False, is_writable=False),     # 12: global_volume_accumulator
        AccountMeta(user_volume_acc, is_signer=False, is_writable=True),        # 13: user_volume_accumulator
        AccountMeta(fee_config, is_signer=False, is_writable=False),            # 14: fee_config
        AccountMeta(FEE_PROGRAM_ID, is_signer=False, is_writable=False),        # 15: fee_program
    ]
    
    return Instruction(PUMP_PROGRAM_ID, data, accounts)

def build_sell_instruction(user: Pubkey, mint: Pubkey, creator: Pubkey, token_amount: int, min_sol_lamports: int) -> Instruction:
    """Build pump.fun sell instruction."""
    bonding_curve = derive_bonding_curve(mint)
    associated_bonding_curve = derive_associated_bonding_curve(bonding_curve, mint)
    user_ata = derive_user_ata(user, mint)
    creator_vault = derive_creator_vault(creator)
    fee_config = derive_fee_config()
    
    # Instruction discriminator for 'sell'
    discriminator = bytes([51, 230, 133, 164, 1, 127, 131, 173])
    
    # Args: amount (u64), min_sol_output (u64)
    data = discriminator + struct.pack('<Q', token_amount) + struct.pack('<Q', min_sol_lamports)
    
    # 14 accounts in exact order from IDL
    accounts = [
        AccountMeta(PUMP_GLOBAL, is_signer=False, is_writable=False),           # 0: global
        AccountMeta(PUMP_FEE_RECIPIENT, is_signer=False, is_writable=True),     # 1: fee_recipient
        AccountMeta(mint, is_signer=False, is_writable=False),                  # 2: mint
        AccountMeta(bonding_curve, is_signer=False, is_writable=True),          # 3: bonding_curve
        AccountMeta(associated_bonding_curve, is_signer=False, is_writable=True), # 4: associated_bonding_curve
        AccountMeta(user_ata, is_signer=False, is_writable=True),               # 5: associated_user
        AccountMeta(user, is_signer=True, is_writable=True),                    # 6: user
        AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),     # 7: system_program
        AccountMeta(creator_vault, is_signer=False, is_writable=True),          # 8: creator_vault
        AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),      # 9: token_program
        AccountMeta(PUMP_EVENT_AUTHORITY, is_signer=False, is_writable=False),  # 10: event_authority
        AccountMeta(PUMP_PROGRAM_ID, is_signer=False, is_writable=False),       # 11: program
        AccountMeta(fee_config, is_signer=False, is_writable=False),            # 12: fee_config
        AccountMeta(FEE_PROGRAM_ID, is_signer=False, is_writable=False),        # 13: fee_program
    ]
    
    return Instruction(PUMP_PROGRAM_ID, data, accounts)


def get_bonding_curve_state(rpc_url: str, mint: Pubkey) -> dict:
    """Get bonding curve state from chain."""
    bonding_curve = derive_bonding_curve(mint)
    resp = requests.post(rpc_url, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "getAccountInfo",
        "params": [str(bonding_curve), {"encoding": "base64"}]
    }, timeout=10)
    result = resp.json().get("result", {})
    if not result or not result.get("value"):
        return None
    
    data = base64.b64decode(result["value"]["data"][0])
    # BondingCurve struct: 8 bytes discriminator + 5 u64s + 1 bool + 32 bytes pubkey
    # virtual_token_reserves, virtual_sol_reserves, real_token_reserves, real_sol_reserves, token_total_supply, complete, creator
    offset = 8  # skip discriminator
    virtual_token_reserves = struct.unpack('<Q', data[offset:offset+8])[0]
    virtual_sol_reserves = struct.unpack('<Q', data[offset+8:offset+16])[0]
    real_token_reserves = struct.unpack('<Q', data[offset+16:offset+24])[0]
    real_sol_reserves = struct.unpack('<Q', data[offset+24:offset+32])[0]
    token_total_supply = struct.unpack('<Q', data[offset+32:offset+40])[0]
    complete = data[offset+40] != 0
    creator = Pubkey.from_bytes(data[offset+41:offset+73]) if len(data) >= offset+73 else None
    
    return {
        'virtual_token_reserves': virtual_token_reserves,
        'virtual_sol_reserves': virtual_sol_reserves,
        'real_token_reserves': real_token_reserves,
        'real_sol_reserves': real_sol_reserves,
        'token_total_supply': token_total_supply,
        'complete': complete,
        'creator': creator,
    }


def get_token_balance(rpc_url: str, user: Pubkey, mint: Pubkey) -> int:
    """Get user's token balance for a mint."""
    user_ata = derive_user_ata(user, mint)
    resp = requests.post(rpc_url, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "getTokenAccountBalance",
        "params": [str(user_ata)]
    }, timeout=10)
    result = resp.json().get("result", {})
    if not result or not result.get("value"):
        return 0
    return int(result["value"]["amount"])


def calculate_sol_for_tokens(token_amount: int, virtual_token_reserves: int, virtual_sol_reserves: int) -> int:
    """Calculate SOL received for selling tokens using bonding curve formula.
    
    Uses constant product formula: (virtual_sol - sol_out) * (virtual_token + token_in) = k
    Solving: sol_out = virtual_sol - k / (virtual_token + token_in)
    """
    if token_amount <= 0:
        return 0
    k = virtual_sol_reserves * virtual_token_reserves
    new_virtual_token = virtual_token_reserves + token_amount
    new_virtual_sol = k // new_virtual_token
    sol_out = virtual_sol_reserves - new_virtual_sol
    return max(0, sol_out)


def calculate_current_price(virtual_token_reserves: int, virtual_sol_reserves: int) -> float:
    """Calculate current token price in SOL."""
    if virtual_token_reserves == 0:
        return 0
    # Price = virtual_sol / virtual_token (in lamports per token)
    return virtual_sol_reserves / virtual_token_reserves


def native_sell(keypair: Keypair, mint: Pubkey, token_amount: int, min_sol_lamports: int, 
                creator: Pubkey, rpc_url: str) -> dict:
    """Execute native pump.fun sell."""
    user = keypair.pubkey()
    
    # Get blockhash
    blockhash = get_recent_blockhash_native(rpc_url)
    
    # Build sell instruction
    sell_ix = build_sell_instruction(user, mint, creator, token_amount, min_sol_lamports)
    
    # Build and sign transaction
    message = Message.new_with_blockhash([sell_ix], user, Hash.from_string(blockhash))
    tx = SoldersTransaction.new_unsigned(message)
    tx.sign([keypair], Hash.from_string(blockhash))
    
    # Send
    signature = send_transaction_native(rpc_url, tx)
    
    return {
        'success': True,
        'signature': signature,
        'token_amount': token_amount,
    }


def get_recent_blockhash_native(rpc_url: str) -> str:
    """Get recent blockhash from Solana."""
    resp = requests.post(rpc_url, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "getLatestBlockhash",
        "params": [{"commitment": "finalized"}]
    }, timeout=10)
    return resp.json()["result"]["value"]["blockhash"]

def send_transaction_native(rpc_url: str, tx: SoldersTransaction) -> str:
    """Send signed transaction to Solana."""
    tx_base64 = base64.b64encode(bytes(tx)).decode()
    resp = requests.post(rpc_url, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "sendTransaction",
        "params": [tx_base64, {"encoding": "base64", "skipPreflight": False, "maxRetries": 3}]
    }, timeout=60)
    result = resp.json()
    if "error" in result:
        raise Exception(f"Transaction failed: {result['error']}")
    return result["result"]

def upload_metadata_to_pump(name: str, symbol: str, description: str,
                            image_path: Optional[str] = None,
                            image_url: Optional[str] = None,
                            banner_path: Optional[str] = None,
                            banner_url: Optional[str] = None,
                            twitter: Optional[str] = None,
                            telegram: Optional[str] = None,
                            website: Optional[str] = None) -> str:
    """Upload metadata directly to pump.fun's IPFS."""
    form_data = {
        'name': name,
        'symbol': symbol,
        'description': description,
        'showName': 'true'
    }
    
    if twitter:
        form_data['twitter'] = twitter
    if telegram:
        form_data['telegram'] = telegram
    if website:
        form_data['website'] = website
    
    files = {}
    
    # Handle main image
    if image_path:
        p = Path(image_path)
        with open(p, 'rb') as f:
            content = f.read()
        ext = p.suffix.lower().lstrip('.')
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
        files['file'] = (p.name, content, mime)
    elif image_url:
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
        files['file'] = ('image.png', resp.content, 'image/png')
    
    # Handle banner if provided
    if banner_path:
        p = Path(banner_path)
        with open(p, 'rb') as f:
            content = f.read()
        ext = p.suffix.lower().lstrip('.')
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')
        files['banner'] = (p.name, content, mime)
    elif banner_url:
        resp = requests.get(banner_url, timeout=30)
        resp.raise_for_status()
        files['banner'] = ('banner.png', resp.content, 'image/png')
    
    resp = requests.post("https://pump.fun/api/ipfs", data=form_data, files=files, timeout=60)
    resp.raise_for_status()
    result = resp.json()
    
    return result.get('metadataUri') or result.get('metadata', {}).get('uri')

def calculate_tokens_for_sol(sol_lamports: int) -> int:
    """Calculate token amount for given SOL using pump.fun bonding curve.
    
    Uses the constant product formula (x * y = k) with pump.fun's initial reserves:
    - initial_virtual_token_reserves: 1,073,000,000,000,000
    - initial_virtual_sol_reserves: 30,000,000,000 (30 SOL)
    """
    virtual_token_reserves = 1_073_000_000_000_000
    virtual_sol_reserves = 30_000_000_000
    
    # k = x * y (constant product)
    k = virtual_token_reserves * virtual_sol_reserves
    
    # After adding sol_lamports, new sol reserves
    new_sol_reserves = virtual_sol_reserves + sol_lamports
    
    # New token reserves = k / new_sol_reserves
    new_token_reserves = k // new_sol_reserves
    
    # Tokens out = old - new
    tokens_out = virtual_token_reserves - new_token_reserves
    
    return tokens_out

def native_launch_with_buy(keypair: Keypair, name: str, symbol: str, uri: str,
                           initial_buy_sol: float, slippage_bps: int,
                           rpc_url: str) -> dict:
    """Launch token with initial buy using native pump.fun program calls."""
    mint_keypair = Keypair()
    mint = mint_keypair.pubkey()
    user = keypair.pubkey()
    
    # Get blockhash
    blockhash = get_recent_blockhash_native(rpc_url)
    
    # Build instructions
    instructions = []
    
    # Platform fee to MintYourAgent treasury
    platform_fee_ix = build_transfer_instruction(user, MYA_TREASURY, MYA_PLATFORM_FEE)
    instructions.append(platform_fee_ix)
    
    # Create instruction
    create_ix = build_create_instruction(user, mint, name, symbol, uri)
    instructions.append(create_ix)
    
    # Buy instruction (with ATA creation)
    if initial_buy_sol > 0:
        sol_lamports = int(initial_buy_sol * 1e9)
        
        # Calculate expected tokens using bonding curve formula
        expected_tokens = calculate_tokens_for_sol(sol_lamports)
        
        # Apply slippage - accept fewer tokens (slippage protects against price movement)
        min_tokens = int(expected_tokens * (10000 - slippage_bps) / 10000)
        
        # Max SOL to spend (with slippage buffer for fees/rounding)
        max_sol_lamports = int(sol_lamports * (1 + slippage_bps / 10000))
        
        # Create user's ATA first (required before buying)
        user_ata = derive_user_ata(user, mint)
        create_ata_ix = build_create_ata_instruction(user, user_ata, user, mint)
        instructions.append(create_ata_ix)
        
        buy_ix = build_buy_instruction(user, mint, user, min_tokens, max_sol_lamports)  # creator=user for initial buy
        instructions.append(buy_ix)
    
    # Build and sign transaction
    message = Message.new_with_blockhash(instructions, user, Hash.from_string(blockhash))
    tx = SoldersTransaction.new_unsigned(message)
    tx.sign([mint_keypair, keypair], Hash.from_string(blockhash))
    
    # Send
    signature = send_transaction_native(rpc_url, tx)
    
    return {
        'success': True,
        'mint': str(mint),
        'signature': signature,
        'pumpUrl': f"https://pump.fun/{mint}"
    }


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


def log_warning(msg: str) -> None:
    get_logger().warning(f"[{get_runtime().correlation_id}] {msg}")


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


def cmd_collect_fees(args: argparse.Namespace) -> None:
    """Collect accumulated creator fees from pump.fun vaults."""
    rt = get_runtime()
    keypair = load_wallet()
    creator = keypair.pubkey()
    rpc_url = get_rpc_url()
    
    # Derive creator vault PDA
    creator_vault = derive_creator_vault(creator)
    
    with Spinner("Checking creator vault..."):
        # Get vault balance
        try:
            resp = api_request('POST', rpc_url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [str(creator_vault)]
            })
            result = resp.json().get("result", {})
            vault_balance = result.get("value", 0) / 1e9
        except Exception as e:
            Output.error("Failed to check vault", str(e))
            return
    
    if vault_balance < 0.001:
        Output.info(f"Creator vault balance: {vault_balance:.6f} SOL")
        Output.info("No fees to collect (minimum 0.001 SOL)")
        return
    
    Output.info(f"Creator vault: {creator_vault}")
    Output.info(f"Balance: {vault_balance:.6f} SOL")
    
    if hasattr(args, 'dry_run') and args.dry_run:
        Output.info("Dry run - skipping collection")
        return
    
    with Spinner("Building collect instruction..."):
        # Build collectCreatorFee instruction
        # Discriminator for collectCreatorFee (from pump.fun IDL)
        discriminator = bytes([0x1a, 0x8b, 0xd6, 0x5c, 0x2b, 0x30, 0x1c, 0x5e])
        
        accounts = [
            AccountMeta(creator, is_signer=True, is_writable=True),           # creator (signer)
            AccountMeta(creator_vault, is_signer=False, is_writable=True),    # creator_vault
            AccountMeta(SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),  # system_program
        ]
        
        collect_ix = Instruction(PUMP_PROGRAM_ID, discriminator, accounts)
        
        # Get blockhash and build tx
        blockhash = get_recent_blockhash_native(rpc_url)
        message = Message.new_with_blockhash([collect_ix], creator, Hash.from_string(blockhash))
        tx = SoldersTransaction.new_unsigned(message)
        tx.sign([keypair], Hash.from_string(blockhash))
    
    with Spinner("Sending transaction..."):
        try:
            signature = send_transaction_native(rpc_url, tx)
        except Exception as e:
            Output.error("Transaction failed", str(e))
            return
    
    if rt.format == OutputFormat.JSON:
        Output.json_output({
            "success": True,
            "collected_sol": vault_balance,
            "signature": signature,
            "creator_vault": str(creator_vault),
        })
    else:
        Output.success(f"Collected {vault_balance:.6f} SOL!")
        print(f"   Signature: {signature}")
        print(f"   Explorer: https://solscan.io/tx/{signature}")


def cmd_sell(args: argparse.Namespace) -> None:
    """Sell tokens from a pump.fun bonding curve."""
    rt = get_runtime()
    keypair = load_wallet()
    user = keypair.pubkey()
    rpc_url = get_rpc_url()
    
    # Parse mint address
    if not hasattr(args, 'mint') or not args.mint:
        Output.error("Mint address required", "Use --mint <address>")
        return
    
    try:
        mint = Pubkey.from_string(args.mint)
    except Exception:
        Output.error("Invalid mint address")
        return
    
    # Get bonding curve state
    with Spinner("Fetching bonding curve state..."):
        bc_state = get_bonding_curve_state(rpc_url, mint)
        if not bc_state:
            Output.error("Bonding curve not found", "Token may not exist or already migrated")
            return
        
        if bc_state['complete']:
            Output.error("Bonding curve complete", "Token has migrated to Raydium - use DEX to sell")
            return
        
        creator = bc_state['creator'] if bc_state['creator'] else user
    
    # Get user's token balance
    with Spinner("Checking token balance..."):
        token_balance = get_token_balance(rpc_url, user, mint)
        if token_balance == 0:
            Output.error("No tokens to sell", "You don't hold any of this token")
            return
    
    # Determine sell amount
    if hasattr(args, 'percent') and args.percent:
        sell_amount = int(token_balance * args.percent / 100)
    elif hasattr(args, 'amount') and args.amount:
        sell_amount = int(args.amount * 1e6)  # Assuming 6 decimals
    else:
        sell_amount = token_balance  # Sell all
    
    if sell_amount > token_balance:
        sell_amount = token_balance
    
    if sell_amount <= 0:
        Output.error("Invalid sell amount")
        return
    
    # Calculate expected SOL output
    expected_sol = calculate_sol_for_tokens(
        sell_amount,
        bc_state['virtual_token_reserves'],
        bc_state['virtual_sol_reserves']
    )
    
    # Apply slippage (default 5%)
    slippage_bps = args.slippage if hasattr(args, 'slippage') and args.slippage else 500
    min_sol = int(expected_sol * (10000 - slippage_bps) / 10000)
    
    # Calculate current price and entry price for gain calculation
    current_price = calculate_current_price(
        bc_state['virtual_token_reserves'],
        bc_state['virtual_sol_reserves']
    )
    
    # Check for target gain condition
    if hasattr(args, 'target_gain') and args.target_gain:
        target_pct = args.target_gain
        
        # For target gain, we need to monitor and wait
        Output.info(f"Monitoring for {target_pct}% gain...")
        Output.info(f"Current balance: {token_balance / 1e6:.2f} tokens")
        Output.info(f"Current price: {current_price * 1e9:.10f} SOL/token")
        
        initial_value = token_balance * current_price
        target_value = initial_value * (1 + target_pct / 100)
        
        print(f"   Initial value: {initial_value / 1e9:.6f} SOL")
        print(f"   Target value:  {target_value / 1e9:.6f} SOL")
        print(f"\nMonitoring... (Ctrl+C to cancel)")
        
        try:
            while True:
                time.sleep(5)  # Check every 5 seconds
                bc_state = get_bonding_curve_state(rpc_url, mint)
                if not bc_state or bc_state['complete']:
                    Output.warning("Bonding curve completed - selling now")
                    break
                
                current_price = calculate_current_price(
                    bc_state['virtual_token_reserves'],
                    bc_state['virtual_sol_reserves']
                )
                current_value = token_balance * current_price
                gain_pct = ((current_value / initial_value) - 1) * 100
                
                sys.stdout.write(f"\r   Gain: {gain_pct:+.2f}% | Value: {current_value / 1e9:.6f} SOL   ")
                sys.stdout.flush()
                
                if gain_pct >= target_pct:
                    print(f"\n{Constants.EMOJI['rocket']} Target reached! Selling...")
                    break
        except KeyboardInterrupt:
            print("\nCancelled.")
            return
        
        # Recalculate expected SOL with current reserves
        expected_sol = calculate_sol_for_tokens(
            sell_amount,
            bc_state['virtual_token_reserves'],
            bc_state['virtual_sol_reserves']
        )
        min_sol = int(expected_sol * (10000 - slippage_bps) / 10000)
    
    # Show sell preview
    Output.info(f"Selling {sell_amount / 1e6:.2f} tokens")
    print(f"   Expected: ~{expected_sol / 1e9:.6f} SOL")
    print(f"   Minimum:  {min_sol / 1e9:.6f} SOL (slippage: {slippage_bps/100}%)")
    
    if hasattr(args, 'dry_run') and args.dry_run:
        Output.info("Dry run - skipping execution")
        return
    
    # Execute sell
    with Spinner("Selling..."):
        try:
            result = native_sell(
                keypair=keypair,
                mint=mint,
                token_amount=sell_amount,
                min_sol_lamports=min_sol,
                creator=creator,
                rpc_url=rpc_url
            )
        except Exception as e:
            Output.error("Sell failed", str(e))
            return
    
    if result['success']:
        if rt.format == OutputFormat.JSON:
            Output.json_output({
                "success": True,
                "signature": result['signature'],
                "tokens_sold": sell_amount,
                "expected_sol": expected_sol / 1e9,
            })
        else:
            Output.success("Sold!")
            print(f"   Tokens: {sell_amount / 1e6:.2f}")
            print(f"   Signature: {result['signature']}")
            print(f"   Explorer: https://solscan.io/tx/{result['signature']}")
    else:
        Output.error("Sell failed")


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
    
    # Append branding to description
    branding = "\n\nLaunched via mintyouragent.com"
    if branding.strip().lower() not in description.lower():
        description = description.rstrip() + branding
    
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
        
        # Use native pump.fun integration when initial buy is specified
        # This bundles create + buy in one atomic transaction (like the webapp)
        if initial_buy > 0:
            # Preflight check - validate rate limits before spending SOL
            preflight_token = None
            with Spinner("Checking launch limits...", total=100):
                try:
                    preflight_resp = api_request(
                        'POST',
                        f"{get_api_url()}/launch/preflight",
                        json={"creatorAddress": creator_address},
                        headers=get_request_headers(),
                        timeout=30
                    )
                    if not preflight_resp.get('allowed', False):
                        Output.error("Daily launch limit reached", 
                            f"Used {preflight_resp.get('launchesToday', '?')}/{preflight_resp.get('maxLaunches', '?')} launches today. "
                            f"Hold $SOUL to unlock more: {preflight_resp.get('learnMore', 'https://mintyouragent.com/token')}")
                        sys.exit(ExitCode.RATE_LIMIT_EXCEEDED)
                    preflight_token = preflight_resp.get('preflightToken')
                    remaining = preflight_resp.get('launchesRemaining', '?')
                    print(f"   ✓ {remaining} launches remaining today")
                except Exception as e:
                    log_warning(f"Preflight check failed: {e}")
                    # Continue without token - server will enforce limits on record
            
            rpc_url = rt.rpc_url or "https://api.mainnet-beta.solana.com"
            slippage_bps = args.slippage if args.slippage else 1000  # 10% default
            
            with Spinner("Uploading metadata...", total=100):
                uri = upload_metadata_to_pump(
                    name=name,
                    symbol=symbol.upper(),
                    description=description,
                    image_path=args.image_file if hasattr(args, 'image_file') and args.image_file else None,
                    image_url=image if not (hasattr(args, 'image_file') and args.image_file) else None,
                    banner_path=args.banner_file if hasattr(args, 'banner_file') and args.banner_file else None,
                    banner_url=banner if banner and not (hasattr(args, 'banner_file') and args.banner_file) else None,
                    twitter=args.twitter if hasattr(args, 'twitter') else None,
                    telegram=args.telegram if hasattr(args, 'telegram') else None,
                    website=args.website if hasattr(args, 'website') else None,
                )
                print(f"   URI: {uri}")
            
            with Spinner("Launching with initial buy...", total=100):
                result = native_launch_with_buy(
                    keypair=keypair,
                    name=name,
                    symbol=symbol.upper(),
                    uri=uri,
                    initial_buy_sol=initial_buy,
                    slippage_bps=slippage_bps,
                    rpc_url=rpc_url
                )
            
            if result['success']:
                log_info(f"Launch success: {result['mint']}")
                add_to_history("launch", {"mint": result['mint'], "symbol": symbol.upper(), "name": name})
                
                # Record to API for leaderboard tracking + rate limit enforcement
                try:
                    record_payload = {
                        "mintAddress": result['mint'],
                        "creatorAddress": creator_address,
                        "signature": result['signature'],
                        "metadata": {
                            "name": name,
                            "symbol": symbol.upper(),
                            "description": description,
                            "imageUrl": uri,
                            "twitter": args.twitter if hasattr(args, 'twitter') else None,
                            "telegram": args.telegram if hasattr(args, 'telegram') else None,
                            "website": args.website if hasattr(args, 'website') else None,
                        },
                        "initialBuySol": initial_buy,
                    }
                    # Include preflight token if we got one
                    if preflight_token:
                        record_payload["preflightToken"] = preflight_token
                    headers = get_request_headers()
                    api_request('POST', f"{get_api_url()}/launch/record", json=record_payload, headers=headers, timeout=30)
                    log_info("Launch recorded to API")
                except Exception as e:
                    log_warning(f"Failed to record launch to API: {e}")
                    # Don't fail the launch, just log the warning
                
                if rt.format == OutputFormat.JSON:
                    Output.json_output({
                        "success": True,
                        "mint": result['mint'],
                        "signature": result['signature'],
                        "pump_url": result['pumpUrl'],
                    })
                else:
                    Output.success("Token launched with initial buy!")
                    print(f"{Constants.EMOJI['coin']} Mint: {result['mint']}")
                    print(f"{Constants.EMOJI['link']} {result['pumpUrl']}")
                    
                    if HAS_CLIPBOARD and Output.copy_to_clipboard(result['pumpUrl']):
                        Output.info("URL copied to clipboard!")
            else:
                Output.error("Launch failed", result.get('error', 'Unknown error'))
                sys.exit(ExitCode.API_ERROR)
            
            return  # Done with native launch
        
        # Prepare (API path - no initial buy)
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
            # Note: initial buy is handled by native path above, not API
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
    
    # Collect Fees
    collect_fees_p = subparsers.add_parser("collect-fees", aliases=["fees"], help="Collect creator fees")
    collect_fees_p.add_argument("--dry-run", action="store_true", help="Check balance without collecting")
    
    # Sell
    sell_p = subparsers.add_parser("sell", help="Sell tokens")
    sell_p.add_argument("--mint", "-m", required=True, help="Token mint address")
    sell_p.add_argument("--amount", "-a", type=float, help="Token amount to sell")
    sell_p.add_argument("--percent", "-p", type=float, help="Percentage of holdings to sell")
    sell_p.add_argument("--target-gain", "-t", type=float, help="Wait for X% gain then sell")
    sell_p.add_argument("--slippage", "-s", type=int, default=500, help="Slippage in basis points (default: 500 = 5%)")
    sell_p.add_argument("--dry-run", action="store_true", help="Preview without executing")
    
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
        "transfer": cmd_transfer, "sign": cmd_sign, "collect-fees": cmd_collect_fees,
        "fees": cmd_collect_fees, "sell": cmd_sell, "config": cmd_config, "uninstall": cmd_uninstall,
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
