#!/usr/bin/env python3
"""README smoke check: real stdio MCP, public FX, then synthetic accounts."""

import asyncio
import os
import sys
import tempfile
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke():
    with tempfile.TemporaryDirectory(prefix="finance-mcp-smoke-") as data_dir:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(
                ("TOSS_", "KIS_", "BINANCE_", "HYPERLIQUID_", "MCP_", "FINANCE_MCP_")
            )
        }
        env.update(FINANCE_MCP_DEMO="1", FINANCE_MCP_DATA_DIR=data_dir)
        server = StdioServerParameters(
            command=sys.executable, args=["-m", "finance_mcp"], env=env
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=90)
            ) as session:
                await session.initialize()
                print("PASS start: stdio initialization", flush=True)
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {
                    "get_market_info",
                    "get_holdings",
                    "get_ticker_research",
                } <= names
                assert len(names) == 28, "expected the curated 28-tool catalog"
                print(f"PASS list: {len(names)} tools", flush=True)
                public = await session.call_tool(
                    "get_market_info",
                    {"include": ["fx"], "base": "USD", "quote": "KRW"},
                )
                assert not public.isError and public.structuredContent["ok"], (
                    "public FX call failed"
                )
                rate = public.structuredContent["data"]["fx"]["rate"]
                assert isinstance(rate, (int, float)) and rate > 0
                print("PASS public: ECB USD/KRW reference rate", flush=True)
                account = await session.call_tool("get_holdings", {})
                assert not account.isError and account.structuredContent["ok"], (
                    "demo account call failed"
                )
                assert account.structuredContent["meta"]["demo"] is True
                assert account.structuredContent["data"]["holdings"]["positions"]
                returns = await session.call_tool(
                    "get_portfolio_returns", {"include_series": True}
                )
                assert not returns.isError and returns.structuredContent["ok"]
                assert returns.structuredContent["data"]["series"]["snapshots"]
                assert (
                    returns.structuredContent["data"]["returns"]["returns"]["twr_pct"]
                    is not None
                )
                print("PASS demo: synthetic holdings and portfolio returns", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(smoke())
    except BaseException as error:
        print(f"FAIL smoke: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
