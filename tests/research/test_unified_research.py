"""All seven mounted tools exercised with generated public-data shaped inputs."""

import math
from datetime import date, datetime, timedelta, timezone

import pytest
from mcp.server.fastmcp import FastMCP

from ticker_engine.market.service import MarketData
from ticker_engine.market.validator import DailyBars, EstimateRow, ProviderDataError
from ticker_engine.mcp_server import register_tools
from ticker_engine.runtime import runtime_dependencies

NOW = datetime(2026, 6, 30, 23, tzinfo=timezone.utc)


class SyntheticYahoo:
    def daily(self, symbol, start, end, now):
        dates = []
        day = start
        while day <= end:
            if day.weekday() < 5:
                dates.append(day)
            day += timedelta(days=1)
        close = tuple(
            100 + (day - date(2020, 1, 1)).days * 0.02 + math.sin(day.toordinal())
            for day in dates
        )
        return DailyBars(
            symbol,
            "USD",
            "America/New_York",
            "EQUITY",
            "Synthetic Issuer",
            "NASDAQ",
            tuple(day.isoformat() for day in dates),
            close,
            tuple(x + 2 for x in close),
            tuple(x - 2 for x in close),
            close,
            tuple(10000.0 for _ in close),
            (),
            (),
            exchange_code="NMS",
        )

    def intraday(self, symbol, now):
        raise ProviderDataError("UPSTREAM_UNAVAILABLE")

    def estimates(self, symbol):
        return [
            EstimateRow("0y", "2026-12-31", 4, 3, 5, 10, 3, "USD"),
            EstimateRow("+1y", "2027-12-31", 5, 4, 6, 10, 4, "USD"),
        ]


class SyntheticSEC:
    failures = []

    def clock(self):
        return NOW

    def close(self):
        pass

    def get_cik(self, ticker):
        return "0000000001"

    def get_company_facts(self, cik):
        return {
            "cik": 1,
            "entityName": "Synthetic Issuer",
            "facts": {
                "us-gaap": {
                    "EarningsPerShareDiluted": {
                        "units": {
                            "USD/shares": [
                                {
                                    "start": f"{year}-01-01",
                                    "end": f"{year}-12-31",
                                    "val": year - 2021,
                                    "accn": f"0000000001-{year % 100:02d}-000001",
                                    "fy": year,
                                    "fp": "FY",
                                    "form": "10-K",
                                    "filed": f"{year + 1}-02-01",
                                    "frame": f"CY{year}",
                                }
                                for year in (2023, 2024, 2025)
                            ]
                        }
                    }
                }
            },
        }

    def get_financials(self, ticker):
        return {
            "entity": {"cik": "0000000001", "name": "Synthetic Issuer"},
            "annuals": [
                {
                    "fiscal_year": 2025,
                    "period_end": "2025-12-31",
                    "filed": "2026-02-01",
                    "revenue": {"value": 100000, "unit": "USD"},
                    "net_income": {"value": 10000, "unit": "USD"},
                }
            ],
        }

    def get_insider_trades(self, ticker, days_back):
        return {
            "transactions": [],
            "summary": {},
            "days_back": days_back,
            "coverage": {"filings_parsed": 0, "skipped_filings": 0, "amendments": 0},
        }


class SyntheticFinancials:
    def close(self):
        pass

    def get_key_metrics(self, ticker):
        return {
            "symbol": ticker,
            "currency": "USD",
            "market_cap": 1000000,
            "trailing_pe": 20,
        }

    def get_ohlcv(self, ticker, period):
        bars = SyntheticYahoo().daily(ticker, date(2025, 6, 30), NOW.date(), NOW)
        return {
            "symbol": ticker,
            "currency": "USD",
            "period": period,
            "period_end": bars.dates[-1],
            "bars": [
                {
                    "time": day,
                    "open": close,
                    "high": close + 2,
                    "low": close - 2,
                    "close": close,
                    "volume": 10000,
                }
                for day, close in zip(bars.dates, bars.closes)
            ],
        }


class SyntheticMarket(MarketData):
    def _consensus_trend(self, symbol):
        return NOW, {"trend": {}, "revisions": {}}

    def _earnings_calendar(self, symbol):
        return NOW, {}


@pytest.fixture
async def mounted():
    sec = SyntheticSEC()
    dependencies = runtime_dependencies(
        sec_client=sec, yfinance_client=SyntheticFinancials(), now=NOW
    )
    market = SyntheticMarket(yahoo=SyntheticYahoo(), sec_client=sec, clock=lambda: NOW)
    dependencies["market_data"] = market
    app = FastMCP("synthetic-research")
    register_tools(app, **dependencies)
    yield app
    await market.aclose()
    await dependencies["fetcher"].aclose()


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("get_ticker_research_status", {}),
        (
            "get_ticker_research",
            {"symbol": "SYN", "confirmed_only": True, "detail": "full"},
        ),
        ("plan_entry", {"symbol": "SYN", "amount": 1000, "confirmed_only": True}),
        ("compare_tickers", {"symbols": ["SYN", "SYNB"], "confirmed_only": True}),
        (
            "compare_price_performance",
            {"symbols": ["SYN", "SYNB"], "confirmed_only": True},
        ),
        ("get_technical_indicators", {"symbol": "SYN", "confirmed_only": True}),
        (
            "get_eps_scenarios",
            {"symbol": "SYN", "confirmed_only": True, "pe_multiples": {"base": 20}},
        ),
    ],
)
async def test_research_tools_succeed_on_synthetic_inputs(mounted, name, arguments):
    result = await mounted.call_tool(name, arguments)
    assert not result.isError, result.structuredContent
    assert result.structuredContent["ok"], result.structuredContent
    if name == "get_ticker_research":
        snapshot = result.structuredContent["data"]["snapshot"]
        for section in (
            "yfinance_bars",
            "yfinance_metrics",
            "sec_financials",
            "sec_insider",
        ):
            assert snapshot["sections"][section]["status"] in {
                "available",
                "partial",
                "empty",
            }, snapshot["sections"][section]
    if name == "get_eps_scenarios":
        assert result.structuredContent["history"]
