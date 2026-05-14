"""Local instrument catalog and autocomplete search."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


CATALOG_PATH = Path(__file__).with_name("instruments.json")


@dataclass(frozen=True)
class Instrument:
    display_name: str
    ticker: str
    asset_type: str
    category: str
    currency: str
    exchange: str
    broker_symbol: str
    api_symbol: str
    leverage_default: float


class InstrumentCatalog:
    def __init__(self, path: Path | str = CATALOG_PATH) -> None:
        self.path = Path(path)
        self.instruments = self._load()

    def _load(self) -> list[Instrument]:
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        return [Instrument(**row) for row in rows]

    def search(self, query: str, limit: int = 8) -> list[Instrument]:
        query = query.strip().lower()
        if not query:
            return []
        scored: list[tuple[int, Instrument]] = []
        for instrument in self.instruments:
            haystack = " ".join(
                [
                    instrument.ticker,
                    instrument.display_name,
                    instrument.asset_type,
                    instrument.category,
                    instrument.exchange,
                    instrument.broker_symbol,
                    instrument.api_symbol,
                ]
            ).lower()
            if query not in haystack:
                continue
            if instrument.ticker.lower().startswith(query):
                score = 0
            elif instrument.display_name.lower().startswith(query):
                score = 1
            else:
                score = 2
            scored.append((score, instrument))
        scored.sort(key=lambda item: (item[0], item[1].ticker))
        return [item[1] for item in scored[:limit]]

    def by_ticker(self, ticker: str) -> Instrument | None:
        ticker = ticker.strip().upper()
        for instrument in self.instruments:
            if instrument.ticker.upper() == ticker or instrument.broker_symbol.upper() == ticker:
                return instrument
        return None
