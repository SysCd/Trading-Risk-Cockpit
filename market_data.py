"""Optional market data providers for Trading Risk Cockpit.

This module never places orders. Providers only return latest available prices
or FX rates for display and calculator prefill.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


ENV_PATH = Path(".env")

PRICE_SYMBOLS = {
    "TSLA": "TSLA",
    "NVDA": "NVDA",
    "AMD": "AMD",
    "MSFT": "MSFT",
    "PLTR": "PLTR",
    "TECH100": "^NDX",
    "NDX": "^NDX",
    "USA500": "^GSPC",
    "SPX": "^GSPC",
    "GER40": "^GDAXI",
    "UK100": "^FTSE",
    "XAGUSD": "SI=F",
    "XAUUSD": "GC=F",
    "OIL": "CL=F",
    "CRUDE": "CL=F",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
}

FX_SYMBOLS = {
    "USD": "GBP=X",
    "EUR": "EURGBP=X",
    "CHF": "CHFGBP=X",
    "JPY": "JPYGBP=X",
    "CAD": "CADGBP=X",
    "AUD": "AUDGBP=X",
    "NZD": "NZDGBP=X",
}


@dataclass
class MarketQuote:
    symbol: str
    value: float
    source: str
    timestamp: str
    delayed: bool = True


class MarketDataProvider(Protocol):
    name: str

    def get_price(self, instrument: str) -> MarketQuote | None:
        ...

    def get_fx_to_gbp(self, currency: str) -> MarketQuote | None:
        ...


class ManualProvider:
    name = "Manual"

    def get_price(self, instrument: str) -> MarketQuote | None:
        return None

    def get_fx_to_gbp(self, currency: str) -> MarketQuote | None:
        if currency.upper() == "GBP":
            return MarketQuote("GBPGBP", 1.0, self.name, _now(), delayed=False)
        return None


class YFinanceProvider:
    name = "yfinance"

    def _ticker_value(self, symbol: str) -> float | None:
        try:
            import yfinance as yf
        except ImportError:
            return None

        ticker = yf.Ticker(symbol)
        try:
            fast_info = ticker.fast_info
            value = fast_info.get("last_price") if hasattr(fast_info, "get") else None
            if value:
                return float(value)
        except Exception:
            pass

        try:
            history = ticker.history(period="1d", interval="1m")
            if not history.empty:
                return float(history["Close"].dropna().iloc[-1])
        except Exception:
            return None
        return None

    def get_price(self, instrument: str) -> MarketQuote | None:
        symbol = PRICE_SYMBOLS.get(instrument.upper())
        if not symbol:
            return None
        value = self._ticker_value(symbol)
        if value is None:
            return None
        return MarketQuote(symbol, value, self.name, _now(), delayed=True)

    def get_fx_to_gbp(self, currency: str) -> MarketQuote | None:
        currency = currency.upper()
        if currency == "GBP":
            return MarketQuote("GBPGBP", 1.0, self.name, _now(), delayed=False)
        symbol = FX_SYMBOLS.get(currency)
        if not symbol:
            return None
        value = self._ticker_value(symbol)
        if value is None:
            return None
        return MarketQuote(symbol, value, self.name, _now(), delayed=True)


class Trading212Provider:
    name = "Trading 212"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def get_price(self, instrument: str) -> MarketQuote | None:
        return None

    def get_fx_to_gbp(self, currency: str) -> MarketQuote | None:
        return None


class IGProvider:
    name = "IG"

    def __init__(self, api_key: str = "", username: str = "", password: str = "", account_type: str = "demo") -> None:
        self.api_key = api_key
        self.username = username
        self.password = password
        self.account_type = account_type

    def get_price(self, instrument: str) -> MarketQuote | None:
        return None

    def get_fx_to_gbp(self, currency: str) -> MarketQuote | None:
        return None


class IBKRProvider:
    name = "IBKR"

    def get_price(self, instrument: str) -> MarketQuote | None:
        return None

    def get_fx_to_gbp(self, currency: str) -> MarketQuote | None:
        return None


class MarketDataService:
    def __init__(self, env_values: dict[str, str] | None = None) -> None:
        env = env_values or load_env()
        self.providers: list[MarketDataProvider] = [
            ManualProvider(),
            YFinanceProvider(),
            Trading212Provider(env.get("TRADING212_API_KEY", "")),
            IGProvider(
                env.get("IG_API_KEY", ""),
                env.get("IG_USERNAME", ""),
                env.get("IG_PASSWORD", ""),
                env.get("IG_ACCOUNT_TYPE", "demo"),
            ),
            IBKRProvider(),
        ]

    def latest_price(self, instrument: str) -> MarketQuote | None:
        for provider in self.providers:
            quote = provider.get_price(instrument)
            if quote is not None:
                return quote
        return None

    def latest_fx_to_gbp(self, currency: str) -> MarketQuote | None:
        for provider in self.providers:
            quote = provider.get_fx_to_gbp(currency)
            if quote is not None:
                return quote
        return None


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_env(path: Path | str = ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path(path)
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def save_env(values: dict[str, str], path: Path | str = ENV_PATH) -> None:
    keys = [
        "TRADING212_API_KEY",
        "IG_API_KEY",
        "IG_USERNAME",
        "IG_PASSWORD",
        "IG_ACCOUNT_TYPE",
        "MARKET_DATA_API_KEY",
    ]
    lines = ["# Local API keys for Trading Risk Cockpit. Do not commit this file."]
    for key in keys:
        lines.append(f"{key}={values.get(key, '')}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
