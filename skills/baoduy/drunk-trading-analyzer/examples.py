#!/usr/bin/env python3
"""Example script for using Trading Analyzer Skill with MCP servers.

This script demonstrates how to programmatically interact with
crypto and stock analysis MCP servers for comprehensive market analysis.
"""

import json
import sys


def run_mcp_command(tool_name: str, params: dict) -> dict:
    """Run a single MCP tool command.
    
    Note: In real usage with OpenClaw, the MCP server runs continuously
    and tools are called via the MCP protocol. This script shows the
    conceptual flow.
    """
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        },
        "id": 1
    }
    
    print(f"MCP Call: {tool_name}")
    print(f"Params: {json.dumps(params, indent=2)}")
    return {"status": "example", "tool": tool_name}


def example_crypto_analysis():
    """Example: Analyze cryptocurrency with technical indicators."""
    print("=== Example: Crypto Analysis (Bitcoin) ===\n")
    
    # Get detailed coin analysis
    run_mcp_command("coin_analysis", {
        "coin": "BTC",
        "exchange": "BINANCE",
        "timeframe": "1D"
    })
    
    # Check for volume breakouts
    print("\n--- Check for volume breakouts ---\n")
    run_mcp_command("smart_volume_scanner", {
        "exchange": "BINANCE",
        "min_volume_ratio": 2.0,
        "min_price_change": 2.0,
        "rsi_range": "any",
        "limit": 10
    })
    
    # Get top gainers for market context
    print("\n--- Check market gainers ---\n")
    run_mcp_command("top_gainers", {
        "exchange": "BINANCE",
        "timeframe": "1h",
        "limit": 5
    })


def example_stock_analysis():
    """Example: Analyze stock with fundamentals and news."""
    print("\n=== Example: Stock Analysis (Apple) ===\n")
    
    # Get company fundamentals
    run_mcp_command("get-ticker-info", {
        "symbol": "AAPL"
    })
    
    # Get latest news
    print("\n--- Fetch latest news ---\n")
    run_mcp_command("get-ticker-news", {
        "symbol": "AAPL",
        "count": 5
    })
    
    # Get earnings information
    print("\n--- Check earnings data ---\n")
    run_mcp_command("ticker-earning", {
        "symbol": "AAPL",
        "period": "quarterly"
    })


def example_market_screening():
    """Example: Screen market for trading opportunities."""
    print("\n=== Example: Market Screening ===\n")
    
    # Find coins with bullish candle patterns
    run_mcp_command("advanced_candle_pattern", {
        "exchange": "KUCOIN",
        "base_timeframe": "15m",
        "pattern_length": 3,
        "min_size_increase": 10,
        "limit": 15
    })
    
    # Find consecutive growing candles (strong uptrend)
    print("\n--- Consecutive bullish candles ---\n")
    run_mcp_command("consecutive_candles_scan", {
        "exchange": "KUCOIN",
        "timeframe": "1h",
        "pattern_type": "bullish",
        "candle_count": 3,
        "min_growth": 2.0,
        "limit": 20
    })


def example_consolidated_report():
    """Example: Build consolidated trading report."""
    print("\n=== Example: Consolidated Trading Report ===\n")
    
    # Step 1: Get crypto price and technical data
    print("Step 1: Fetch crypto technical analysis\n")
    crypto_data = run_mcp_command("coin_analysis", {
        "coin": "ETH",
        "exchange": "BINANCE",
        "timeframe": "4h"
    })
    
    # Step 2: Check volume confirmation
    print("\nStep 2: Verify volume confirmation\n")
    volume_data = run_mcp_command("volume_confirmation_analysis", {
        "coin": "ETH",
        "exchange": "BINANCE"
    })
    
    # Step 3: Build comprehensive report
    print("\nStep 3: Consolidated Analysis Result\n")
    report = {
        "symbol": "ETHUSDT",
        "timestamp": "2026-02-10T17:30:00Z",
        "price": {
            "current": 2450.50,
            "24h_change": -3.2,
            "24h_high": 2550.00,
            "24h_low": 2380.00
        },
        "technical": "Bearish (from coin_analysis)",
        "volume": "Confirmed (from volume_confirmation)",
        "recommendation": "HOLD",
        "support": 2350.00,
        "resistance": 2550.00,
        "risk_level": "Moderate"
    }
    print(json.dumps(report, indent=2))


def example_multi_asset_comparison():
    """Example: Compare multiple assets."""
    print("\n=== Example: Multi-Asset Comparison ===\n")
    
    symbols = ["AAPL", "MSFT", "TSLA"]
    
    print("Fetching data for tech stocks...\n")
    results = []
    
    for symbol in symbols:
        print(f"Analyzing {symbol}...")
        ticker_data = run_mcp_command("get-ticker-info", {
            "symbol": symbol
        })
        results.append({
            "symbol": symbol,
            "status": "analyzed"
        })
    
    print("\n--- Comparison Summary ---")
    print(json.dumps(results, indent=2))


def main():
    """Run examples."""
    print("Trading Analyzer Skill - Usage Examples")
    print("=" * 60)
    print()
    print("Note: These are conceptual examples showing MCP tool calls.")
    print("In practice, OpenClaw manages the MCP server lifecycle.")
    print()
    
    example_crypto_analysis()
    example_stock_analysis()
    example_market_screening()
    example_consolidated_report()
    example_multi_asset_comparison()
    
    print("\n" + "=" * 60)
    print("For actual usage, configure MCP servers in .vscode/mcp.json")
    print("Then use AI agent to call these tools and consolidate results.")


if __name__ == "__main__":
    main()
