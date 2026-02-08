"""
AlphaBot Agent Handler
Market intelligence, price tracking, and alpha discovery
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from datetime import datetime


class Chain(Enum):
    ETHEREUM = 1
    BASE = 8453
    POLYGON = 137
    ARBITRUM = 42161


class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"
    WHALE_MOVE = "whale_move"
    NEW_LAUNCH = "new_launch"


@dataclass
class TokenPrice:
    address: str
    chain: Chain
    symbol: str
    name: str
    price_usd: Decimal
    price_native: Decimal
    change_24h: float
    volume_24h: Decimal
    liquidity_usd: Decimal
    market_cap: Optional[Decimal] = None
    fdv: Optional[Decimal] = None


@dataclass
class PriceAlert:
    alert_id: str
    user_id: str
    token_address: str
    chain: Chain
    alert_type: AlertType
    target_value: Decimal
    created_at: datetime
    triggered: bool = False
    triggered_at: Optional[datetime] = None


@dataclass
class WhaleTransaction:
    tx_hash: str
    wallet: str
    token_address: str
    chain: Chain
    action: str  # buy, sell, transfer
    amount: Decimal
    value_usd: Decimal
    timestamp: datetime


PAYMENT_WALLET = "0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9"


class AlphaBotHandler:
    """Main handler for AlphaBot agent"""
    
    def __init__(self):
        self.config = self._load_config()
        self._price_cache: Dict[str, TokenPrice] = {}
        
    def _load_config(self) -> Dict[str, Any]:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r") as f:
            return json.load(f)
    
    async def check_subscription(self, user_id: str) -> Dict[str, Any]:
        """Check if user has active subscription"""
        return {
            "active": False,
            "plan": None,
            "expires_at": None,
            "payment_required": True,
            "payment_wallet": PAYMENT_WALLET
        }
    
    async def generate_payment_request(self, user_id: str, plan: str, chain: Chain) -> Dict[str, Any]:
        """Generate payment request for subscription"""
        pricing = self.config["pricing"]["plans"].get(plan)
        if not pricing:
            raise ValueError(f"Invalid plan: {plan}")
            
        return {
            "user_id": user_id,
            "plan": plan,
            "amount_usd": pricing["price_usd"],
            "payment_wallet": PAYMENT_WALLET,
            "chain": chain.name.lower(),
            "accepted_tokens": self.config["pricing"]["accepted_tokens"],
            "memo": f"alphabot_{plan}_{user_id}"
        }
    
    async def get_price(
        self,
        token: str,  # Address or symbol
        chain: Optional[Chain] = None
    ) -> TokenPrice:
        """Get token price"""
        
        # Try DexScreener first
        price_data = await self._fetch_dexscreener_price(token, chain)
        
        if not price_data:
            # Fallback to CoinGecko for major tokens
            price_data = await self._fetch_coingecko_price(token)
        
        if not price_data:
            raise ValueError(f"Token not found: {token}")
        
        return price_data
    
    async def _fetch_dexscreener_price(
        self,
        token: str,
        chain: Optional[Chain]
    ) -> Optional[TokenPrice]:
        """Fetch price from DexScreener"""
        # Integration point for DexScreener API
        return None
    
    async def _fetch_coingecko_price(self, token: str) -> Optional[TokenPrice]:
        """Fetch price from CoinGecko"""
        # Integration point for CoinGecko API
        return None
    
    async def create_alert(
        self,
        user_id: str,
        token_address: str,
        chain: Chain,
        alert_type: AlertType,
        target_value: Decimal
    ) -> PriceAlert:
        """Create price alert"""
        
        # Check alert limits
        user_alerts = await self._get_user_alerts(user_id)
        max_alerts = self.config["alerts"]["max_alerts_per_user"]
        
        if len(user_alerts) >= max_alerts:
            raise ValueError(f"Maximum {max_alerts} alerts allowed")
        
        alert = PriceAlert(
            alert_id=f"alert_{user_id}_{len(user_alerts)}",
            user_id=user_id,
            token_address=token_address,
            chain=chain,
            alert_type=alert_type,
            target_value=target_value,
            created_at=datetime.utcnow()
        )
        
        # Save alert
        await self._save_alert(alert)
        
        return alert
    
    async def delete_alert(self, user_id: str, alert_id: str) -> bool:
        """Delete price alert"""
        # Integration point for alert storage
        return True
    
    async def get_alerts(self, user_id: str) -> List[PriceAlert]:
        """Get user's alerts"""
        return await self._get_user_alerts(user_id)
    
    async def _get_user_alerts(self, user_id: str) -> List[PriceAlert]:
        """Get all alerts for user"""
        return []
    
    async def _save_alert(self, alert: PriceAlert) -> None:
        """Save alert to storage"""
        pass
    
    async def get_trending(
        self,
        chain: Optional[Chain] = None,
        limit: int = 10
    ) -> List[TokenPrice]:
        """Get trending tokens"""
        # Integration point for trending data
        return []
    
    async def get_new_launches(
        self,
        chain: Optional[Chain] = None,
        hours: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recently launched tokens"""
        # Integration point for new token detection
        return []
    
    async def track_whale(
        self,
        wallet: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Add whale wallet to tracking"""
        return {
            "success": True,
            "wallet": wallet,
            "tracking": True
        }
    
    async def get_whale_transactions(
        self,
        wallet: Optional[str] = None,
        chain: Optional[Chain] = None,
        limit: int = 20
    ) -> List[WhaleTransaction]:
        """Get whale transactions"""
        return []
    
    async def get_smart_money_moves(
        self,
        chain: Optional[Chain] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get smart money wallet movements"""
        return []
    
    async def get_portfolio(
        self,
        wallet: str,
        chain: Optional[Chain] = None
    ) -> Dict[str, Any]:
        """Get portfolio for wallet"""
        return {
            "wallet": wallet,
            "total_value_usd": 0,
            "holdings": [],
            "pnl_24h": 0,
            "pnl_7d": 0
        }


def _price_to_dict(price: TokenPrice) -> Dict[str, Any]:
    """Convert TokenPrice to dictionary"""
    return {
        "address": price.address,
        "chain": price.chain.name,
        "symbol": price.symbol,
        "name": price.name,
        "price_usd": str(price.price_usd),
        "price_native": str(price.price_native),
        "change_24h": price.change_24h,
        "volume_24h": str(price.volume_24h),
        "liquidity_usd": str(price.liquidity_usd),
        "market_cap": str(price.market_cap) if price.market_cap else None,
        "fdv": str(price.fdv) if price.fdv else None
    }


def _alert_to_dict(alert: PriceAlert) -> Dict[str, Any]:
    """Convert PriceAlert to dictionary"""
    return {
        "alert_id": alert.alert_id,
        "token_address": alert.token_address,
        "chain": alert.chain.name,
        "alert_type": alert.alert_type.value,
        "target_value": str(alert.target_value),
        "created_at": alert.created_at.isoformat(),
        "triggered": alert.triggered
    }


async def handle_command(
    command: str,
    args: Dict[str, Any],
    user_id: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Main entry point for bot commands"""
    
    handler = AlphaBotHandler()
    
    # Some commands are free (basic price check)
    free_commands = ["price"]
    
    if command not in free_commands:
        subscription = await handler.check_subscription(user_id)
        if subscription["payment_required"]:
            return {
                "action": "payment_required",
                "message": "🔐 AlphaBot requires an active subscription",
                "pricing": handler.config["pricing"]["plans"],
                "payment_wallet": PAYMENT_WALLET
            }
    
    chain = Chain(args["chain_id"]) if args.get("chain_id") else None
    
    if command == "price":
        token = args.get("token") or args.get("address") or args.get("symbol")
        if not token:
            return {"error": "Token address or symbol required"}
        
        try:
            price = await handler.get_price(token, chain)
            return _price_to_dict(price)
        except ValueError as e:
            return {"error": str(e)}
    
    elif command == "create_alert":
        alert = await handler.create_alert(
            user_id,
            args["token_address"],
            chain or Chain.BASE,
            AlertType(args["alert_type"]),
            Decimal(args["target_value"])
        )
        return _alert_to_dict(alert)
    
    elif command == "delete_alert":
        success = await handler.delete_alert(user_id, args["alert_id"])
        return {"success": success}
    
    elif command == "alerts":
        alerts = await handler.get_alerts(user_id)
        return {"alerts": [_alert_to_dict(a) for a in alerts]}
    
    elif command == "trending":
        tokens = await handler.get_trending(chain, args.get("limit", 10))
        return {"trending": [_price_to_dict(t) for t in tokens]}
    
    elif command == "new_launches":
        launches = await handler.get_new_launches(
            chain,
            args.get("hours", 24),
            args.get("limit", 20)
        )
        return {"launches": launches}
    
    elif command == "whale":
        if args.get("wallet"):
            return await handler.track_whale(args["wallet"], user_id)
        else:
            transactions = await handler.get_whale_transactions(
                args.get("filter_wallet"),
                chain,
                args.get("limit", 20)
            )
            return {"transactions": [
                {
                    "tx_hash": t.tx_hash,
                    "wallet": t.wallet,
                    "action": t.action,
                    "value_usd": str(t.value_usd)
                }
                for t in transactions
            ]}
    
    elif command == "portfolio":
        return await handler.get_portfolio(args["wallet"], chain)
    
    return {"error": f"Unknown command: {command}"}
