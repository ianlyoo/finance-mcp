"""Synthetic fixtures only, isolated state, and no network in unit tests."""

import json
import os
import socket
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_RUNTIME = tempfile.TemporaryDirectory(prefix="finance-mcp-tests-")
for name in tuple(os.environ):
    if name.startswith(
        ("TOSS_", "KIS_", "BINANCE_", "MCP_", "FINANCE_MCP_", "HYPERLIQUID_")
    ):
        os.environ.pop(name, None)
os.environ["FINANCE_MCP_DATA_DIR"] = _RUNTIME.name
os.environ["XDG_CACHE_HOME"] = _RUNTIME.name


@pytest.fixture(autouse=True)
def no_live_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Outgoing network is forbidden in synthetic tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    import curl_cffi.requests

    monkeypatch.setattr(curl_cffi.requests.Session, "request", blocked)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_MCP_DATA_DIR", str(tmp_path))
    from finance_mcp import provider_pacing, toss_api

    for name in ("SEC_BUDGET", "BINANCE_BUDGET"):
        current = getattr(provider_pacing, name)
        monkeypatch.setattr(
            provider_pacing, name, provider_pacing.RequestBudget(current.interval)
        )
    monkeypatch.setattr(
        toss_api,
        "_RATE_BUDGETS",
        {
            group: provider_pacing.RequestBudget(budget.interval)
            for group, budget in toss_api._RATE_BUDGETS.items()
        },
    )


@pytest.fixture
def load_fixture():
    def load(name):
        if name not in {"daily-bars.synthetic.json", "bars-invalid.synthetic.json"}:
            raise ValueError("Unknown synthetic fixture")
        return json.loads((Path(__file__).parent / "fixtures" / name).read_text())

    return load
