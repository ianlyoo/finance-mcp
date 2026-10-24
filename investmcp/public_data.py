"""Public reference FX and no-key Yahoo market data."""

import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import httpx
import yfinance as yf

from investmcp.kinvest_common import YFINANCE_LOCK, synchronized

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def exchange_rate(base="USD", quote="KRW"):
    base, quote = base.upper(), quote.upper()
    if not all(re.fullmatch(r"[A-Z]{3}", value) for value in (base, quote)):
        raise ValueError("Currencies must be three-letter ISO codes")
    with httpx.Client(timeout=20) as client:
        response = client.get(ECB_URL)
        response.raise_for_status()
    rates = {"EUR": 1.0}
    as_of = None
    for cube in ET.fromstring(response.content).iter():
        if "time" in cube.attrib:
            as_of = cube.attrib["time"]
        if "currency" in cube.attrib:
            rate = float(cube.attrib["rate"])
            if math.isfinite(rate) and rate > 0:
                rates[cube.attrib["currency"]] = rate
    if not as_of or base not in rates or quote not in rates:
        raise ValueError("Requested currency unavailable in ECB reference rates")
    return {
        "base": base,
        "quote": quote,
        "rate": rates[quote] / rates[base],
        "as_of": as_of,
        "source": "European Central Bank",
        "source_url": ECB_URL,
        "basis": "daily reference rate; not a live or executable quote",
    }


def yahoo_symbol(symbol):
    symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=-]{0,24}", symbol):
        raise ValueError("Invalid public market symbol")
    return symbol + ".KS" if re.fullmatch(r"\d{6}", symbol) else symbol


@synchronized(YFINANCE_LOCK)
def quote(symbol):
    ticker = yf.Ticker(yahoo_symbol(symbol))
    info = ticker.fast_info
    price = float(info["last_price"])
    if not math.isfinite(price) or price <= 0:
        raise ValueError("Quote unavailable")
    return {
        "symbol": symbol.upper(),
        "price": price,
        "currency": info["currency"],
        "source": "Yahoo Finance via yfinance (unofficial)",
        "price_time": None,
        "warning": "Provider observation time unavailable; quote may be delayed",
    }


@synchronized(YFINANCE_LOCK)
def candles(
    symbol,
    interval="1d",
    count=100,
    adjusted=True,
    before=None,
    start_date=None,
    end_date=None,
):
    if interval not in {"1d", "1m"} or not 1 <= count <= 200:
        raise ValueError("Use interval 1d/1m and count 1..200")
    options = {
        "interval": interval,
        "auto_adjust": adjusted,
        "actions": False,
        "timeout": 15,
    }
    if start_date:
        options["start"] = datetime.fromisoformat(start_date).date().isoformat()
        if end_date:
            options["end"] = (
                datetime.fromisoformat(end_date).date() + timedelta(days=1)
            ).isoformat()
    else:
        options["period"] = "5d" if interval == "1m" else "1y"
    history = yf.Ticker(yahoo_symbol(symbol)).history(**options)
    rows = []
    for when, row in history.iterrows():
        label = when.isoformat()
        if before and label > before or end_date and label[:10] > end_date:
            continue
        values = {
            field: float(row[field.title()])
            for field in ("open", "high", "low", "close", "volume")
        }
        if all(math.isfinite(value) for value in values.values()):
            rows.append({"timestamp": label, **values})
    return {
        "symbol": symbol.upper(),
        "candles": rows[-count:],
        "source": "Yahoo Finance via yfinance (unofficial)",
        "interval": interval,
        "adjusted": adjusted,
        "complete": False,
        "warning": "Daily OHLCV may include an incomplete session; Yahoo minute history is limited",
    }
