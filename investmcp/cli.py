"""Console entry point; no configuration files are implicitly loaded."""

import argparse
import os
from contextlib import asynccontextmanager


def main():
    parser = argparse.ArgumentParser(description="InvestMCP: read-only investing MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=os.environ.get("INVESTMCP_TRANSPORT", "stdio"),
    )
    parser.add_argument(
        "--host", default=os.environ.get("INVESTMCP_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("INVESTMCP_PORT", "18800"))
    )
    parser.add_argument("--version", action="version", version="investmcp 0.1.0")
    args = parser.parse_args()
    os.umask(0o077)
    if (
        args.transport == "streamable-http"
        and not os.environ.get("MCP_AUTH_TOKEN", "").strip()
    ):
        parser.error(
            "HTTP requires MCP_AUTH_TOKEN; set a strong random bearer token in the environment."
        )
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    import yfinance

    from investmcp.kinvest_common import cache_dir

    yfinance.set_tz_cache_location(str(cache_dir() / "yfinance"))
    from investmcp import server

    server.mcp.settings.host = args.host
    server.mcp.settings.port = args.port
    original_lifespan = server.mcp._mcp_server.lifespan

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with original_lifespan(app) as context:
                yield context
        finally:
            dependencies = server._research_dependencies
            await dependencies["market_data"].aclose()
            await dependencies["fetcher"].aclose()
            for client in (
                server._sec_client,
                server._yf_client,
                server._binance_client,
                server._toss_client,
            ):
                if client is not None and hasattr(client, "close"):
                    client.close()

    server.mcp._mcp_server.lifespan = lifespan
    server.mcp.run(transport=args.transport)
