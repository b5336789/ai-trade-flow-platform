"""In-memory store of user-imported OHLCV history, keyed by (market, symbol).

Lets 台股 / 美股 be paper-traded and backtested offline with your own CSV data, without needing
a live broker API. Process-local (cleared on restart) — fine for the current single-node setup.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from app.schemas import Candle, MarketKind

_store: dict[tuple[MarketKind, str], list[Candle]] = {}


def _parse_timestamp(raw: str) -> datetime:
    raw = raw.strip()
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass
    # epoch seconds or milliseconds
    try:
        value = int(float(raw))
        if value > 10_000_000_000:  # ms
            value //= 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"unparseable timestamp: {raw!r}") from exc


def parse_csv(text: str) -> list[Candle]:
    """Parse OHLCV CSV with header: timestamp,open,high,low,close[,volume]. Fail loud on bad rows."""
    reader = csv.DictReader(io.StringIO(text.strip()))
    if reader.fieldnames is None:
        raise ValueError("CSV is empty")
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - {f.strip().lower() for f in reader.fieldnames}
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")

    candles: list[Candle] = []
    for i, row in enumerate(reader, start=2):  # row 1 is the header
        norm = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        try:
            candles.append(
                Candle(
                    timestamp=_parse_timestamp(norm["timestamp"]),
                    open=float(norm["open"]),
                    high=float(norm["high"]),
                    low=float(norm["low"]),
                    close=float(norm["close"]),
                    volume=float(norm.get("volume") or 0.0),
                )
            )
        except (ValueError, KeyError) as exc:
            raise ValueError(f"CSV row {i} invalid: {exc}") from exc
    if not candles:
        raise ValueError("CSV has a header but no data rows")
    candles.sort(key=lambda c: c.timestamp)
    return candles


def set_candles(market: MarketKind, symbol: str, candles: list[Candle]) -> None:
    _store[(market, symbol)] = candles


def get_candles(market: MarketKind, symbol: str) -> list[Candle] | None:
    return _store.get((market, symbol))


def has_market_data(market: MarketKind) -> bool:
    return any(m == market for (m, _s) in _store)


def list_symbols(market: MarketKind) -> list[str]:
    return [s for (m, s) in _store if m == market]


def clear() -> None:
    _store.clear()
