"""
Fetch OHLCV klines and current price from the public Binance REST API (no auth).

Endpoints used:
  GET https://api.binance.com/api/v3/klines        — historical candles
  GET https://api.binance.com/api/v3/ticker/price  — current best price
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

logger = logging.getLogger("CRYPTO_BOT")

_KLINES_URL = "https://api.binance.com/api/v3/klines"
_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"
_MAX_PER_REQUEST = 1000

_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "number_of_trades",
    "taker_buy_base_volume", "taker_buy_quote_volume", "ignore",
]

# Maps pandas-ta / raw column names → clean feature names used by the models.
# Must stay in sync with store_features.COLUMN_MAP.
COLUMN_RENAME: Dict[str, str] = {
    "RSI_14":          "rsi_14",
    "MACD_12_26_9":    "macd",
    "MACDh_12_26_9":   "macd_hist",
    "MACDs_12_26_9":   "macd_signal",
    "BBL_20_2.0_2.0":  "bb_lower",
    "BBM_20_2.0_2.0":  "bb_mid",
    "BBU_20_2.0_2.0":  "bb_upper",
    "BBB_20_2.0_2.0":  "bb_bandwidth",
    "BBP_20_2.0_2.0":  "bb_percent",
    # Fallback for older pandas_ta versions
    "BBL_20_2.0":      "bb_lower",
    "BBM_20_2.0":      "bb_mid",
    "BBU_20_2.0":      "bb_upper",
    "BBB_20_2.0":      "bb_bandwidth",
    "BBP_20_2.0":      "bb_percent",
    "EMA_9":           "ema_9",
    "EMA_21":          "ema_21",
    "EMA_55":          "ema_55",
    "SMA_20":          "sma_20",
    "SMA_50":          "sma_50",
    "SMA_200":         "sma_200",
    "ATRr_14":         "atr_14",
}


def fetch_klines(
    symbol: str,
    interval: str = "1m",
    limit: int = 500,
) -> pd.DataFrame:
    """
    Fetch up to `limit` klines for symbol/interval from Binance (public API).

    Automatically paginates when limit > 1 000.

    Returns DataFrame with columns: open_time (UTC datetime), open, high,
    low, close, volume — sorted ascending by open_time.
    """
    all_rows: List[List[Any]] = []
    remaining = limit
    params: Dict[str, Any] = {"symbol": symbol, "interval": interval}

    while remaining > 0:
        batch_size = min(remaining, _MAX_PER_REQUEST)
        params["limit"] = batch_size

        # If we already have data, fetch older candles (go backwards)
        if all_rows:
            params["endTime"] = int(all_rows[0][0]) - 1

        try:
            resp = requests.get(_KLINES_URL, params=params, timeout=15)
            resp.raise_for_status()
            batch: List[List[Any]] = resp.json()
        except requests.RequestException as exc:
            logger.error(f"Binance klines request failed: {exc}")
            break

        if not batch:
            break

        all_rows = batch + all_rows  # prepend older candles
        remaining -= len(batch)

        if len(batch) < batch_size:
            break  # reached oldest available data

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=_KLINE_COLS)
    df["open_time"] = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)

    return (
        df[["open_time", "open", "high", "low", "close", "volume"]]
        .sort_values("open_time")
        .drop_duplicates("open_time")
        .reset_index(drop=True)
    )


def fetch_current_price(symbol: str) -> Dict[str, Any]:
    """Return the latest best price for a symbol via the Binance ticker endpoint."""
    try:
        resp = requests.get(_TICKER_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "symbol": data["symbol"],
            "price": float(data["price"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except requests.RequestException as exc:
        logger.error(f"Binance ticker request failed: {exc}")
        raise
