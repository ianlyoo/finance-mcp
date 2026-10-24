"""Release contracts with synthetic inputs and zero outbound network."""

import ast
import json
import re
from pathlib import Path

import httpx
import pytest
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from investmcp import server
from investmcp.demo import ACCOUNT_TOOLS, LOCAL_WRITERS


def required_arguments(name):
    parameters = server.mcp._tool_manager.get_tool(name).parameters
    values = {
        "start_date": "2026-01-01",
        "end_date": "2026-02-01",
        "file": "synthetic.pdf",
    }
    return {
        key: parameters["properties"][key].get("enum", [values.get(key, "synthetic")])[
            0
        ]
        for key in parameters.get("required", [])
    }


async def test_every_tool_is_read_only_except_explicit_local_writers():
    tools = await server.mcp.list_tools()
    assert len(tools) == 28
    expected = {public for public, _ in server.tools_v2.CHAT_TOOLS} | {
        "get_ticker_research",
        "get_ticker_research_status",
        "plan_entry",
        "compare_tickers",
        "compare_price_performance",
        "get_technical_indicators",
        "get_eps_scenarios",
    }
    assert {tool.name for tool in tools} == expected
    assert set(server.mcp._tool_manager._tools) == expected
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is (tool.name not in LOCAL_WRITERS), (
            tool.name
        )
        assert tool.annotations.destructiveHint is False
        assert not re.match(
            r"^(place|create_order|submit|execute|cancel|amend|buy|sell|trade|transfer|withdraw)_",
            tool.name,
        )
    assert len({tool.name for tool in tools}) == len(tools)


@pytest.mark.parametrize("name", sorted(ACCOUNT_TOOLS))
async def test_missing_account_configuration_is_clear(name):
    arguments = required_arguments(name)
    response = await server.mcp.call_tool(name, arguments)
    assert response.isError
    assert response.structuredContent["error"]["code"] == "NOT_CONFIGURED"
    assert "set " in response.structuredContent["error"]["message"]


@pytest.mark.parametrize(
    "name",
    sorted(
        ACCOUNT_TOOLS
        - {"apply_statement_import", "preview_statement_import", "import_statement"}
    ),
)
async def test_demo_account_tools_have_no_network_and_are_labelled(name, monkeypatch):
    monkeypatch.setenv("INVESTMCP_DEMO", "1")
    result = await server.mcp.call_tool(name, required_arguments(name))
    assert result.structuredContent["ok"], (name, result)
    assert result.structuredContent["meta"]["demo"] is True
    assert result.structuredContent["meta"]["provider"] == "synthetic"
    json.dumps(result.structuredContent, allow_nan=False)


async def test_demo_pnl_uses_real_engine_and_known_synthetic_cashflows(monkeypatch):
    monkeypatch.setenv("INVESTMCP_DEMO", "1")
    pnl = (await server.mcp.call_tool("get_trading_pnl", {})).structuredContent["data"][
        "by_symbol"
    ]
    assert pnl["totals"]["realized_pnl_krw"] == 52000
    assert not pnl["incomplete_cost_basis"]
    performance = (
        await server.mcp.call_tool("get_portfolio_returns", {"include_series": True})
    ).structuredContent["data"]
    assert len(performance["series"]["snapshots"]) == 31
    assert performance["returns"]["returns"]["twr_pct"] == pytest.approx(
        (1 / 0.95 - 1) * 100, abs=0.0001
    )


async def test_invalid_demo_arguments_are_validated(monkeypatch):
    monkeypatch.setenv("INVESTMCP_DEMO", "1")
    with pytest.raises(ToolError):
        await server.mcp.call_tool("get_portfolio_returns", {"period": "invalid"})


def test_data_directory_and_demo_snapshot_are_separate(tmp_path, monkeypatch):
    from investmcp.kinvest_common import cache_dir
    from investmcp.portfolio_store import default_db_path

    monkeypatch.setenv("INVESTMCP_DATA_DIR", str(tmp_path))
    assert cache_dir() == tmp_path
    assert default_db_path() == tmp_path / "portfolio.db"


def test_official_broker_mutation_endpoints_are_absent():
    root = Path(__file__).resolve().parents[1] / "investmcp"
    for name in (
        "kis_api.py",
        "toss_api.py",
        "binance_futures_api.py",
        "crypto_futures_accounts.py",
    ):
        tree = ast.parse((root / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                assert not re.match(
                    r"^(place_order|cancel_order|submit_order|withdraw|transfer_funds)$",
                    node.name,
                )
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value not in {
                    "/fapi/v1/order",
                    "/fapi/v1/batchOrders",
                    "/sapi/v1/capital/withdraw/apply",
                    "/uapi/domestic-stock/v1/trading/order-cash",
                    "/exchange",
                }
    from investmcp.crypto_futures_accounts import BINANCE_ALLOWLIST

    assert all(method == "GET" for method, _ in BINANCE_ALLOWLIST)


def test_toss_send_rejects_mutation_before_network():
    from investmcp.toss_api import TossClient

    client = TossClient("synthetic-id", "synthetic-secret")
    with pytest.raises(ValueError, match="Read-only"):
        client._send("POST", "/api/v1/orders")
    client.close()


async def test_bearer_http_rejects_missing_and_wrong_token():
    verifier = server.StaticTokenVerifier("synthetic-test-access")
    app_server = FastMCP(
        "synthetic",
        token_verifier=verifier,
        auth=AuthSettings(
            validate_token_resource=False,
            issuer_url="http://localhost:18899",
            resource_server_url="http://localhost:18899",
        ),
        stateless_http=True,
    )

    @app_server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def ping() -> str:
        return "pong"

    app = app_server.streamable_http_app()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost:18899"
        ) as client:
            for headers in ({}, {"Authorization": "Bearer incorrect"}):
                response = await client.post(
                    "/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                )
                assert response.status_code == 401
    assert await verifier.verify_token("synthetic-test-access") is not None


@pytest.mark.parametrize(
    "name",
    [
        "get_help",
        "get_toss_holdings",
        "get_kis_accounts",
        "get_binance_futures_quote",
        "get_market_series",
        "get_quote_v2",
        "get_portfolio_summary_v2",
    ],
)
async def test_legacy_names_are_not_callable(name):
    with pytest.raises(ToolError, match="Unknown tool"):
        await server.mcp.call_tool(name, {})
