"""Entirely synthetic account data; calculations use the same portfolio engine.

Symbols, labels, amounts, and transactions below were invented for this project.
No account provider or network client is instantiated by this module.
"""

import os
from datetime import date, timedelta

from investmcp import portfolio_engine as engine
from investmcp.portfolio_model import (
    CashBalance,
    FxRates,
    Holding,
    Transaction,
    TxType,
)
from investmcp.portfolio_sources import Collection

ACCOUNT_TOOLS = frozenset(
    {
        "get_holdings",
        "get_portfolio_summary",
        "get_portfolio_returns",
        "get_transactions",
        "get_trading_pnl",
        "get_crypto_positions",
        "get_crypto_account_history",
        "snapshot_portfolio_nav",
        "export_portfolio_dataset",
        "import_statement",
    }
)
LOCAL_WRITERS = frozenset(
    {"snapshot_portfolio_nav", "export_portfolio_dataset", "import_statement"}
)


def enabled():
    return os.environ.get("INVESTMCP_DEMO", "").lower() in {"1", "true"}


def _configured(name):
    toss = bool(
        os.environ.get("TOSS_ACCOUNTS_JSON")
        or (os.environ.get("TOSS_CLIENT_ID") and os.environ.get("TOSS_CLIENT_SECRET"))
    )
    kis = bool(
        os.environ.get("KIS_ACCOUNTS_JSON")
        or (
            os.environ.get("KIS_APP_KEY")
            and os.environ.get("KIS_APP_SECRET")
            and os.environ.get("KIS_CANO")
        )
    )
    crypto = bool(
        os.environ.get("BINANCE_API_KEY")
        and (
            os.environ.get("BINANCE_API_SECRET")
            or os.environ.get("BINANCE_SIGNING_KEY")
        )
    )
    crypto = crypto or bool(os.environ.get("HYPERLIQUID_ACCOUNT_ADDRESSES"))
    if "toss" in name or "statement" in name:
        return toss, "TOSS_CLIENT_ID and TOSS_CLIENT_SECRET (or TOSS_ACCOUNTS_JSON)"
    if "kis" in name:
        return kis, "KIS_APP_KEY, KIS_APP_SECRET and KIS_CANO (or KIS_ACCOUNTS_JSON)"
    if "crypto" in name:
        return crypto, "BINANCE_API_KEY and BINANCE_API_SECRET (or BINANCE_SIGNING_KEY)"
    return (
        toss or kis or crypto,
        "TOSS_CLIENT_ID and TOSS_CLIENT_SECRET, or KIS_APP_KEY/KIS_APP_SECRET/KIS_CANO, or BINANCE_API_KEY/BINANCE_API_SECRET",
    )


def synthetic_portfolio(arguments=None):
    arguments = arguments or {}
    today = date.today()
    start = today - timedelta(days=30)
    fx = FxRates(rates={"USD": 1300.0, "KRW": 1.0}, as_of=today.isoformat())
    holdings = [
        Holding(
            "toss",
            "DEMO-TOSS-1",
            "DEMOUS",
            "USD",
            8,
            name="Synthetic US Works",
            market="US",
            last_price=110,
            avg_price=100,
            cost_basis=800,
            market_value=880,
            unrealized_pnl=80,
        ),
        Holding(
            "kis",
            "DEMO-KIS-1",
            "DEMO-KR",
            "KRW",
            15,
            name="Synthetic KR Works",
            market="KR",
            last_price=22000,
            avg_price=20000,
            cost_basis=300000,
            market_value=330000,
            unrealized_pnl=30000,
        ),
    ]
    cash = [
        CashBalance("toss", "DEMO-TOSS-1", "USD", 500),
        CashBalance("kis", "DEMO-KIS-1", "KRW", 100000),
    ]
    transactions = []
    for holding, quantity in zip(holdings, (10, 15)):
        transactions.append(
            Transaction(
                holding.provider,
                holding.account,
                "DEMO-BUY-" + holding.symbol,
                TxType.BUY,
                start.isoformat(),
                holding.currency,
                symbol=holding.symbol,
                quantity=quantity,
                price=holding.avg_price,
                gross_amount=quantity * holding.avg_price,
                net_amount=-quantity * holding.avg_price,
                fx_rate=fx.rate(holding.currency),
                fee_status="reported",
                tax_status="reported",
                source="synthetic",
            )
        )
    transactions.append(
        Transaction(
            "toss",
            "DEMO-TOSS-1",
            "DEMO-SELL-1",
            TxType.SELL,
            (today - timedelta(days=10)).isoformat(),
            "USD",
            symbol="DEMOUS",
            quantity=2,
            price=120,
            gross_amount=240,
            net_amount=240,
            fx_rate=1300,
            fee_status="reported",
            tax_status="reported",
            source="synthetic",
        )
    )
    account = arguments.get("account")
    accounts = arguments.get("accounts")
    if account and account not in {"all", "primary", "auto"}:
        accounts = [account]
    if accounts:
        holdings = [row for row in holdings if row.account in accounts]
        cash = [row for row in cash if row.account in accounts]
        transactions = [row for row in transactions if row.account in accounts]
    if arguments.get("symbol"):
        holdings = [row for row in holdings if row.symbol == arguments["symbol"]]
        transactions = [
            row for row in transactions if row.symbol == arguments["symbol"]
        ]
    return holdings, cash, transactions, fx, start.isoformat(), today.isoformat()


def account_result(name, arguments):
    if name not in ACCOUNT_TOOLS:
        return None
    if not enabled():
        configured, variables = _configured(name)
        if configured:
            return None
        return {
            "ok": False,
            "data": None,
            "error": {
                "code": "NOT_CONFIGURED",
                "message": f"Account not configured: set {variables}; or set INVESTMCP_DEMO=1.",
            },
            "meta": {"server_version": "0.1.0"},
        }
    if "statement" in name:
        return {
            "ok": False,
            "data": None,
            "error": {
                "code": "DEMO_LOCAL_IMPORT_UNAVAILABLE",
                "message": "Demo transactions are generated in code. Statement import requires your configured Toss account.",
            },
            "meta": {"demo": True},
        }
    holdings, cash, transactions, fx, start, end = synthetic_portfolio(arguments)
    start = arguments.get("start") or start
    end = arguments.get("end") or end
    consolidated = engine.consolidate_holdings(holdings, fx)
    realized = engine.compute_realized_pnl(transactions, fx, start, end)
    summary = engine.summarize_portfolio(holdings, cash, fx, realized)
    total = summary["total_assets_krw"]
    # A generated complete zero-external-flow window, with known synthetic NAVs.
    navs = [
        {
            "snapshot_date": (
                date.fromisoformat(start) + timedelta(days=i)
            ).isoformat(),
            "total_value_krw": total
            * (
                0.95
                + 0.05
                * i
                / max(1, (date.fromisoformat(end) - date.fromisoformat(start)).days)
            ),
            "result_status": "complete",
            "snapshot_id": "DEMO-NAV-" + str(i),
        }
        for i in range(
            max(
                0,
                min(
                    366, (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
                ),
            )
        )
    ]
    performance = engine.compute_performance(
        transactions,
        navs,
        total,
        fx,
        start,
        end,
        realized,
        external_cashflows_coverage={
            "status": "verified_zero",
            "source": "synthetic_generator",
            "start": start,
            "end": end,
        },
    )
    if name == "get_trading_pnl":
        if arguments.get("view") == "round_trips":
            health = {row.account: {"status": "ok"} for row in holdings}
            ledger = Collection(
                transactions=transactions,
                health=health,
                fetch_complete=True,
                requested_window={"start": start, "end": end},
            )
            positions = Collection(
                holdings=holdings, cash=cash, health=health, fetch_complete=True
            )
            data = {
                "round_trips": engine.compute_trade_review(
                    ledger,
                    positions,
                    fx,
                    start,
                    end,
                    symbol=arguments.get("symbol", ""),
                    detail_level=arguments.get("detail_level", "summary"),
                )
            }
        else:
            data = {"by_symbol": realized}
    elif name == "get_portfolio_returns":
        data = {"returns": performance}
        if arguments.get("include_series"):
            data["series"] = {"snapshots": navs, "performance": performance}
    elif name == "get_portfolio_summary":
        sections = {
            "totals": summary,
            "realized": realized,
            "concentration": engine.concentration_risk(consolidated),
            "exposure": {"positions": consolidated["positions"]},
        }
        data = {
            key: sections[key]
            for key in arguments.get("sections", ["totals", "realized"])
        }
    elif "crypto" in name:
        data = {
            "venue": "binance",
            "account": "DEMO-BINANCE-1",
            "positions": [],
            "fills": [],
            "funding_payments": [],
            "wallet_balance": 250,
            "currency": "USDT",
            "status": "demo",
        }
    elif name == "get_transactions":
        rows = [row.to_dict() for row in transactions if start <= row.trade_date <= end]
        data = {"transactions": rows[: arguments.get("limit", 100)], "total": len(rows)}
    elif name == "snapshot_portfolio_nav":
        from investmcp.kinvest_common import cache_dir
        from investmcp.portfolio_store import NavStore

        data = NavStore(cache_dir() / "demo" / "portfolio.db").upsert_snapshot(
            summary, snapshot_date=arguments.get("snapshot_date") or end, fx_usdkrw=1300
        )
    elif name == "export_portfolio_dataset":
        data = {
            "holdings": consolidated,
            "transactions": [row.to_dict() for row in transactions],
            "summary": summary,
            "storage": "demo response only",
        }
    else:
        data = {"holdings": consolidated}
        if arguments.get("include_cash", True):
            data["cash"] = {"balances": [row.to_dict() for row in cash]}
    return {
        "ok": True,
        "data": data,
        "error": None,
        "meta": {
            "demo": True,
            "server_version": "0.1.0",
            "provider": "synthetic",
            "note": "Invented data; generated 30-day NAV and ledger history, synthetic prices and FX. No broker requests.",
        },
    }
