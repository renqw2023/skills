#!/usr/bin/env python3
"""
ERC-8004 Identity Registry CLI

Register agents on-chain, update metadata, and validate registrations.
"""

import argparse
import base64
import json
import os
import sys
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

# Chain configurations
CHAINS = {
    "base": {"id": 8453, "rpc": "https://mainnet.base.org", "explorer": "https://basescan.org"},
    "ethereum": {"id": 1, "rpc": "https://ethereum-rpc.publicnode.com", "explorer": "https://etherscan.io"},
    "polygon": {"id": 137, "rpc": "https://polygon-rpc.com", "explorer": "https://polygonscan.com"},
    "monad": {"id": 143, "rpc": "https://rpc.monad.xyz", "explorer": "https://explorer.monad.xyz"},
    "bnb": {"id": 56, "rpc": "https://bsc-rpc.publicnode.com", "explorer": "https://bscscan.com"},
}

# ERC-8004 Identity Registry contract (same on all chains)
REGISTRY_ADDRESS = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

# ERC-8004 Identity Registry ABI (from spec)
REGISTRY_ABI = [
    # register() - returns agentId
    {
        "name": "register",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable"
    },
    # register(string agentURI) - returns agentId
    {
        "name": "register",
        "type": "function",
        "inputs": [{"name": "agentURI", "type": "string"}],
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable"
    },
    # setAgentURI(uint256 agentId, string newURI)
    {
        "name": "setAgentURI",
        "type": "function",
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "newURI", "type": "string"}
        ],
        "outputs": [],
        "stateMutability": "nonpayable"
    },
    # tokenURI(uint256 tokenId) - ERC-721 standard
    {
        "name": "tokenURI",
        "type": "function",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view"
    },
    # ownerOf(uint256 tokenId) - ERC-721 standard
    {
        "name": "ownerOf",
        "type": "function",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view"
    },
    # Transfer event (ERC-721) - agentId is topics[3]
    {
        "name": "Transfer",
        "type": "event",
        "inputs": [
            {"name": "from", "type": "address", "indexed": True},
            {"name": "to", "type": "address", "indexed": True},
            {"name": "tokenId", "type": "uint256", "indexed": True}
        ]
    },
    # Registered event
    {
        "name": "Registered",
        "type": "event",
        "inputs": [
            {"name": "agentId", "type": "uint256", "indexed": True},
            {"name": "agentURI", "type": "string", "indexed": False},
            {"name": "owner", "type": "address", "indexed": True}
        ]
    },
    # URIUpdated event
    {
        "name": "URIUpdated",
        "type": "event",
        "inputs": [
            {"name": "agentId", "type": "uint256", "indexed": True},
            {"name": "newURI", "type": "string", "indexed": False},
            {"name": "updatedBy", "type": "address", "indexed": True}
        ]
    }
]

def check_dependencies():
    """Check for required dependencies."""
    try:
        from web3 import Web3
        from eth_account import Account
        return True
    except ImportError:
        print("Error: Missing dependencies. Install with:")
        print("  pip install web3 eth-account")
        return False

def get_wallet():
    """Get wallet from environment variables."""
    from eth_account import Account

    mnemonic = os.environ.get("ERC8004_MNEMONIC")
    private_key = os.environ.get("ERC8004_PRIVATE_KEY")

    if mnemonic:
        Account.enable_unaudited_hdwallet_features()
        account = Account.from_mnemonic(mnemonic)
        return account
    elif private_key:
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        return Account.from_key(private_key)
    else:
        print("Error: Set ERC8004_MNEMONIC or ERC8004_PRIVATE_KEY environment variable")
        sys.exit(1)

def get_web3(chain: str):
    """Get Web3 instance for chain."""
    from web3 import Web3

    if chain not in CHAINS:
        print(f"Error: Unknown chain '{chain}'. Available: {', '.join(CHAINS.keys())}")
        sys.exit(1)

    rpc = CHAINS[chain]["rpc"]
    w3 = Web3(Web3.HTTPProvider(rpc))

    if not w3.is_connected():
        print(f"Error: Could not connect to {chain} RPC at {rpc}")
        sys.exit(1)

    return w3

def get_contract(w3):
    """Get ERC-8004 Identity Registry contract instance."""
    return w3.eth.contract(
        address=w3.to_checksum_address(REGISTRY_ADDRESS),
        abi=REGISTRY_ABI
    )

def build_registration_json(name: str, description: str, image: Optional[str] = None,
                            services: Optional[List[Dict]] = None,
                            registrations: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Build ERC-8004 compliant registration JSON."""
    data = {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "name": name,
        "description": description,
        "image": image or "",
        "services": services or [],
        "x402Support": False,
        "active": True,
        "registrations": registrations or [],
        "supportedTrust": ["reputation"]
    }
    return data

def encode_data_uri(data: Dict[str, Any]) -> str:
    """Encode JSON data as base64 data URI."""
    json_str = json.dumps(data, separators=(',', ':'))
    b64 = base64.b64encode(json_str.encode()).decode()
    return f"data:application/json;base64,{b64}"

def decode_data_uri(uri: str) -> Optional[Dict[str, Any]]:
    """Decode base64 data URI to JSON."""
    if uri.startswith("data:application/json;base64,"):
        b64 = uri.replace("data:application/json;base64,", "")
        try:
            json_str = base64.b64decode(b64).decode()
            return json.loads(json_str)
        except Exception as e:
            print(f"Warning: Could not decode data URI: {e}")
            return None
    elif uri.startswith("http://") or uri.startswith("https://"):
        # Fetch from URL
        try:
            req = urllib.request.Request(uri, headers={"User-Agent": "ERC8004-CLI/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"Warning: Could not fetch URI: {e}")
            return None
    else:
        # Try to parse as raw JSON
        try:
            return json.loads(uri)
        except:
            return None

def parse_agent_id_from_receipt(w3, receipt) -> Optional[int]:
    """Parse agentId from Transfer event in transaction receipt."""
    # Transfer event topic (keccak256 of "Transfer(address,address,uint256)")
    transfer_topic = w3.keccak(text="Transfer(address,address,uint256)").hex()

    for log in receipt.logs:
        if len(log.topics) >= 4:
            # Check if this is a Transfer event
            if log.topics[0].hex() == transfer_topic:
                # agentId is in topics[3] (tokenId for ERC-721 mint)
                agent_id = int(log.topics[3].hex(), 16)
                return agent_id

    return None

def send_transaction(w3, account, tx_data: Dict) -> str:
    """Sign and send a transaction, return tx hash."""
    # Build transaction
    tx = {
        "from": account.address,
        "to": tx_data.get("to"),
        "data": tx_data.get("data"),
        "gas": tx_data.get("gas", 500000),
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": w3.eth.chain_id,
    }

    if "value" in tx_data:
        tx["value"] = tx_data["value"]

    # Estimate gas
    try:
        estimated = w3.eth.estimate_gas(tx)
        tx["gas"] = int(estimated * 1.2)  # 20% buffer
    except Exception as e:
        error_msg = str(e).lower()
        if "insufficient funds" in error_msg:
            print(f"Error: Insufficient funds in wallet {account.address}")
            sys.exit(1)
        elif "not owner" in error_msg or "unauthorized" in error_msg:
            print("Error: You are not the owner of this agent")
            sys.exit(1)
        else:
            print(f"Error estimating gas: {e}")
            sys.exit(1)

    # Sign and send
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    return tx_hash.hex()

def wait_for_receipt(w3, tx_hash: str, timeout: int = 120):
    """Wait for transaction receipt."""
    return w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

def cmd_register(args):
    """Register a new agent on-chain."""
    if not check_dependencies():
        sys.exit(1)

    chain = args.chain or "base"
    w3 = get_web3(chain)
    account = get_wallet()
    contract = get_contract(w3)
    chain_info = CHAINS[chain]

    print(f"Registering agent on {chain}...")
    print(f"  Wallet: {account.address}")

    # Step 1: Call register() to get agentId
    print("\nStep 1: Calling register() to mint agent NFT...")

    # Use register() without URI first
    register_fn = contract.functions.register()
    tx_data = {
        "to": REGISTRY_ADDRESS,
        "data": register_fn._encode_transaction_data(),
    }

    tx_hash = send_transaction(w3, account, tx_data)
    print(f"  Transaction: {tx_hash}")
    print(f"  Waiting for confirmation...")

    receipt = wait_for_receipt(w3, tx_hash)

    if receipt.status != 1:
        print("Error: Registration transaction failed")
        sys.exit(1)

    # Parse agentId from Transfer event
    agent_id = parse_agent_id_from_receipt(w3, receipt)
    if agent_id is None:
        print("Error: Could not parse agentId from transaction logs")
        sys.exit(1)

    print(f"  Agent ID: {agent_id}")

    # Step 2: Build full JSON with registrations array
    print("\nStep 2: Setting agent URI with full metadata...")

    registration_entry = {
        "agentId": agent_id,
        "agentRegistry": f"eip155:{chain_info['id']}:{REGISTRY_ADDRESS}"
    }

    reg_json = build_registration_json(
        name=args.name,
        description=args.description,
        image=args.image,
        registrations=[registration_entry]
    )

    data_uri = encode_data_uri(reg_json)

    # Call setAgentURI
    set_uri_fn = contract.functions.setAgentURI(agent_id, data_uri)
    tx_data = {
        "to": REGISTRY_ADDRESS,
        "data": set_uri_fn._encode_transaction_data(),
    }

    tx_hash2 = send_transaction(w3, account, tx_data)
    print(f"  Transaction: {tx_hash2}")
    print(f"  Waiting for confirmation...")

    receipt2 = wait_for_receipt(w3, tx_hash2)

    if receipt2.status != 1:
        print("Error: setAgentURI transaction failed")
        sys.exit(1)

    # Success output
    print("\n" + "="*50)
    print("Agent registered successfully!")
    print("="*50)
    print(f"  Agent ID: {agent_id}")
    print(f"  Chain: {chain} ({chain_info['id']})")
    print(f"  Owner: {account.address}")
    print(f"  Registry: {REGISTRY_ADDRESS}")
    print(f"\n  Register TX: {chain_info['explorer']}/tx/{receipt.transactionHash.hex()}")
    print(f"  SetURI TX: {chain_info['explorer']}/tx/{receipt2.transactionHash.hex()}")
    print(f"\n  Metadata:")
    print(f"    Name: {args.name}")
    print(f"    Description: {args.description}")
    if args.image:
        print(f"    Image: {args.image}")

def cmd_update(args):
    """Update an existing agent's metadata."""
    if not check_dependencies():
        sys.exit(1)

    chain = args.chain or "base"
    w3 = get_web3(chain)
    account = get_wallet()
    contract = get_contract(w3)
    chain_info = CHAINS[chain]

    agent_id = int(args.agent_id)

    print(f"Updating agent {agent_id} on {chain}...")

    # Check ownership
    try:
        owner = contract.functions.ownerOf(agent_id).call()
        if owner.lower() != account.address.lower():
            print(f"Error: You are not the owner of agent {agent_id}")
            print(f"  Owner: {owner}")
            print(f"  Your address: {account.address}")
            sys.exit(1)
    except Exception as e:
        if "ERC721" in str(e) or "invalid" in str(e).lower():
            print(f"Error: Agent {agent_id} does not exist")
        else:
            print(f"Error checking ownership: {e}")
        sys.exit(1)

    # Get current URI
    try:
        current_uri = contract.functions.tokenURI(agent_id).call()
        current_data = decode_data_uri(current_uri)
    except Exception as e:
        print(f"Warning: Could not read current URI: {e}")
        current_data = None

    if current_data is None:
        current_data = build_registration_json(
            name="Unknown",
            description="",
            registrations=[{
                "agentId": agent_id,
                "agentRegistry": f"eip155:{chain_info['id']}:{REGISTRY_ADDRESS}"
            }]
        )

    # Apply updates
    if args.name:
        current_data["name"] = args.name
    if args.description:
        current_data["description"] = args.description
    if args.image:
        current_data["image"] = args.image

    # Handle service updates
    if args.add_service:
        if "services" not in current_data:
            current_data["services"] = []
        # Parse service: name=X,endpoint=Y
        parts = dict(p.split("=", 1) for p in args.add_service.split(","))
        current_data["services"].append(parts)

    if args.remove_service:
        if "services" in current_data:
            current_data["services"] = [
                s for s in current_data["services"]
                if s.get("name") != args.remove_service
            ]

    # Ensure required fields
    if "type" not in current_data:
        current_data["type"] = "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
    if "registrations" not in current_data or not current_data["registrations"]:
        current_data["registrations"] = [{
            "agentId": agent_id,
            "agentRegistry": f"eip155:{chain_info['id']}:{REGISTRY_ADDRESS}"
        }]

    # Encode and submit
    data_uri = encode_data_uri(current_data)

    set_uri_fn = contract.functions.setAgentURI(agent_id, data_uri)
    tx_data = {
        "to": REGISTRY_ADDRESS,
        "data": set_uri_fn._encode_transaction_data(),
    }

    tx_hash = send_transaction(w3, account, tx_data)
    print(f"  Transaction: {tx_hash}")
    print(f"  Waiting for confirmation...")

    receipt = wait_for_receipt(w3, tx_hash)

    if receipt.status != 1:
        print("Error: Update transaction failed")
        sys.exit(1)

    print("\n" + "="*50)
    print("Agent updated successfully!")
    print("="*50)
    print(f"  Agent ID: {agent_id}")
    print(f"  TX: {chain_info['explorer']}/tx/{receipt.transactionHash.hex()}")
    print(f"\n  Updated metadata:")
    print(f"    Name: {current_data.get('name', 'N/A')}")
    print(f"    Description: {current_data.get('description', 'N/A')}")
    if current_data.get("image"):
        print(f"    Image: {current_data['image']}")
    if current_data.get("services"):
        print(f"    Services: {len(current_data['services'])}")

def cmd_info(args):
    """Display agent information."""
    if not check_dependencies():
        sys.exit(1)

    chain = args.chain or "base"
    w3 = get_web3(chain)
    contract = get_contract(w3)
    chain_info = CHAINS[chain]

    agent_id = int(args.agent_id)

    print(f"Agent {agent_id} on {chain}")
    print("="*50)

    # Get owner
    try:
        owner = contract.functions.ownerOf(agent_id).call()
        print(f"Owner: {owner}")
    except Exception as e:
        err = str(e)
        if "ERC721" in err or "invalid" in err.lower() or "0x7e273289" in err:
            print(f"Error: Agent {agent_id} does not exist on {chain}")
        else:
            print(f"Error: {err}")
        sys.exit(1)

    # Get URI
    try:
        uri = contract.functions.tokenURI(agent_id).call()
    except Exception as e:
        print(f"Error reading tokenURI: {e}")
        sys.exit(1)

    # Decode and display
    data = decode_data_uri(uri)

    if data:
        print(f"\nMetadata:")
        print(f"  Type: {data.get('type', 'N/A')}")
        print(f"  Name: {data.get('name', 'N/A')}")
        print(f"  Description: {data.get('description', 'N/A')}")
        print(f"  Image: {data.get('image', 'N/A')}")
        print(f"  Active: {data.get('active', 'N/A')}")
        print(f"  x402 Support: {data.get('x402Support', 'N/A')}")

        if data.get("services"):
            print(f"\n  Services ({len(data['services'])}):")
            for svc in data["services"]:
                print(f"    - {svc.get('name', 'unnamed')}: {svc.get('endpoint', 'N/A')}")

        if data.get("registrations"):
            print(f"\n  Registrations ({len(data['registrations'])}):")
            for reg in data["registrations"]:
                print(f"    - Agent {reg.get('agentId')} @ {reg.get('agentRegistry', 'N/A')}")

        if data.get("supportedTrust"):
            print(f"\n  Supported Trust: {', '.join(data['supportedTrust'])}")
    else:
        print(f"\nRaw URI: {uri[:100]}..." if len(uri) > 100 else f"\nRaw URI: {uri}")

    print(f"\nRegistry: {REGISTRY_ADDRESS}")
    print(f"Explorer: {chain_info['explorer']}/token/{REGISTRY_ADDRESS}?a={agent_id}")

def cmd_validate(args):
    """Validate agent registration for common issues."""
    if not check_dependencies():
        sys.exit(1)

    chain = args.chain or "base"
    w3 = get_web3(chain)
    contract = get_contract(w3)

    agent_id = int(args.agent_id)

    print(f"Validating agent {agent_id} on {chain}...")
    print("="*50)

    issues = []
    warnings = []

    # Check existence
    try:
        owner = contract.functions.ownerOf(agent_id).call()
    except Exception:
        print("FAIL: Agent does not exist")
        sys.exit(1)

    # Get URI
    try:
        uri = contract.functions.tokenURI(agent_id).call()
    except Exception as e:
        issues.append(f"Cannot read tokenURI: {e}")
        uri = ""

    # Decode
    data = decode_data_uri(uri) if uri else None

    if not data:
        issues.append("Could not decode metadata (invalid JSON or URI format)")
    else:
        # Check required fields
        if not data.get("type"):
            issues.append("Missing 'type' field")
        elif data["type"] != "https://eips.ethereum.org/EIPS/eip-8004#registration-v1":
            warnings.append(f"Non-standard type: {data['type']}")

        if not data.get("name"):
            issues.append("Missing or empty 'name' field")

        if not data.get("description"):
            warnings.append("Missing or empty 'description' field")

        # Check registrations array
        if not data.get("registrations"):
            issues.append("Missing 'registrations' array")
        else:
            has_self = False
            for reg in data["registrations"]:
                if reg.get("agentId") == agent_id:
                    has_self = True
                    break
            if not has_self:
                warnings.append(f"registrations[] does not include this agentId ({agent_id})")

        # Check image
        image = data.get("image", "")
        if image:
            # Check for local paths
            if image.startswith("/") or image.startswith("./") or image.startswith("../"):
                issues.append(f"Image is a local path (not accessible): {image}")
            elif image.startswith("file://"):
                issues.append(f"Image is a file:// URL (not accessible): {image}")
            elif image.startswith("http://") or image.startswith("https://"):
                # Try to reach the image
                try:
                    req = urllib.request.Request(image, method="HEAD",
                                                 headers={"User-Agent": "ERC8004-Validator/1.0"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status >= 400:
                            warnings.append(f"Image URL returned status {resp.status}")
                except urllib.error.HTTPError as e:
                    warnings.append(f"Image URL not reachable: HTTP {e.code}")
                except urllib.error.URLError as e:
                    warnings.append(f"Image URL not reachable: {e.reason}")
                except Exception as e:
                    warnings.append(f"Could not verify image URL: {e}")
        else:
            warnings.append("No image URL set")

    # Report results
    print()
    if issues:
        print("ISSUES (should fix):")
        for issue in issues:
            print(f"  [X] {issue}")

    if warnings:
        print("\nWARNINGS (consider fixing):")
        for warning in warnings:
            print(f"  [!] {warning}")

    if not issues and not warnings:
        print("PASS: No issues found")
    elif not issues:
        print(f"\nResult: PASS with {len(warnings)} warning(s)")
    else:
        print(f"\nResult: FAIL ({len(issues)} issue(s), {len(warnings)} warning(s))")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="ERC-8004 Identity Registry CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Register a new agent:
    %(prog)s register --name "MyAgent" --description "AI assistant" --image "https://example.com/avatar.jpg"

  Update agent metadata:
    %(prog)s update 123 --name "NewName" --description "Updated description"

  Add a service to agent:
    %(prog)s update 123 --add-service "name=api,endpoint=https://api.example.com"

  View agent info:
    %(prog)s info 123

  Validate agent registration:
    %(prog)s validate 123

Environment:
  ERC8004_MNEMONIC      - BIP39 mnemonic phrase for wallet
  ERC8004_PRIVATE_KEY   - Private key (alternative to mnemonic)
"""
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # register command
    reg_parser = subparsers.add_parser("register", help="Register a new agent")
    reg_parser.add_argument("--name", required=True, help="Agent name")
    reg_parser.add_argument("--description", required=True, help="Agent description")
    reg_parser.add_argument("--image", help="Image URL (https://...)")
    reg_parser.add_argument("--chain", choices=CHAINS.keys(), default="base",
                           help="Blockchain to use (default: base)")

    # update command
    upd_parser = subparsers.add_parser("update", help="Update agent metadata")
    upd_parser.add_argument("agent_id", help="Agent ID to update")
    upd_parser.add_argument("--name", help="New agent name")
    upd_parser.add_argument("--description", help="New description")
    upd_parser.add_argument("--image", help="New image URL")
    upd_parser.add_argument("--add-service", help="Add service (format: name=X,endpoint=Y)")
    upd_parser.add_argument("--remove-service", help="Remove service by name")
    upd_parser.add_argument("--chain", choices=CHAINS.keys(), default="base",
                           help="Blockchain to use (default: base)")

    # info command
    info_parser = subparsers.add_parser("info", help="Display agent information")
    info_parser.add_argument("agent_id", help="Agent ID to query")
    info_parser.add_argument("--chain", choices=CHAINS.keys(), default="base",
                            help="Blockchain to use (default: base)")

    # validate command
    val_parser = subparsers.add_parser("validate", help="Validate agent registration")
    val_parser.add_argument("agent_id", help="Agent ID to validate")
    val_parser.add_argument("--chain", choices=CHAINS.keys(), default="base",
                           help="Blockchain to use (default: base)")

    args = parser.parse_args()

    if args.command == "register":
        cmd_register(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "validate":
        cmd_validate(args)

if __name__ == "__main__":
    main()
