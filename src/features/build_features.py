import logging
import numpy as np
from typing import Optional

import pandas as pd
import pandas_ta as ta  # noqa: F401  — registers df.ta accessor

logger = logging.getLogger("CRYPTO_BOT")
logging.basicConfig(level=logging.INFO)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to an OHLCV DataFrame using pandas-ta.

    Expected input columns: open, high, low, close, volume.
    Appended columns (examples):
      RSI_14, MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9,
      BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0,
      EMA_9, EMA_21, EMA_55, SMA_20, SMA_50, SMA_200, ATRr_14.
    """
    df = df.copy()

    # RSI
    df.ta.rsi(length=14, append=True)

    # MACD
    df.ta.macd(fast=12, slow=26, signal=9, append=True)

    # Bollinger Bands
    df.ta.bbands(length=20, std=2, append=True)

    # EMA
    for length in [9, 21, 55]:
        df.ta.ema(length=length, append=True)

    # SMA
    for length in [20, 50, 200]:
        df.ta.sma(length=length, append=True)

    # ATR
    df.ta.atr(length=14, append=True)

    return df


def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add temporal features derived from the open_time column.

    Appended columns:
      hour          — 0–23
      day_of_week   — 0 (Mon) – 6 (Sun)
      hour_sin, hour_cos       — cyclical encoding of hour (period 24)
      dow_sin,  dow_cos        — cyclical encoding of day of week (period 7)
    """
    df = df.copy()

    ts = pd.to_datetime(df["open_time"], utc=True)
    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    return df


def compute_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add lag return features based on close price.

    Lags of 1, 4, and 24 periods correspond to 1h, 4h, and 24h on a 1h timeframe.
    Uses simple percentage returns: (close[t] - close[t-n]) / close[t-n].

    Appended columns: return_1h, return_4h, return_24h.
    """
    df = df.copy()
    df["return_1h"] = df["close"].pct_change(1)
    df["return_4h"] = df["close"].pct_change(4)
    df["return_24h"] = df["close"].pct_change(24)
    return df


def load_ohlcv_from_mongo(symbol: str) -> pd.DataFrame:
    """Load and sort historical OHLCV data for one symbol from MongoDB."""
    from src.data.config import SETTINGS
    from src.data.connector.connector import connect_to_mongo, read_from_mongo

    db_name = SETTINGS["MONGO_DB"]
    host = SETTINGS["MONGO_HOST"]
    port = int(SETTINGS["MONGO_PORT"])
    user = SETTINGS.get("MONGO_USER", "")
    password = SETTINGS.get("MONGO_PASSWORD", "")
    auth = bool(user)

    client = connect_to_mongo(
        db_name=db_name, host=host, port=port, auth=auth, user=user, password=password
    )
    db = client[db_name]
    collection = SETTINGS["MONGO_COLLECTION_HISTORICAL"]

    df = read_from_mongo(db, collection, query={"symbol": symbol})
    client.close()

    if df.empty:
        logger.warning(f"No data found in MongoDB for {symbol}")
        return df

    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def build_features(symbol: str) -> pd.DataFrame:
    """
    Load OHLCV data for a symbol from MongoDB and compute all technical indicators.

    Returns the enriched DataFrame, or an empty DataFrame if no source data found.
    """
    logger.info(f"Building features for {symbol}")
    df = load_ohlcv_from_mongo(symbol)
    if df.empty:
        return df

    df = compute_technical_indicators(df)
    df = compute_temporal_features(df)
    df = compute_lag_features(df)
    logger.info(
        f"{symbol}: {len(df)} rows, {len(df.columns)} columns after feature engineering"
    )
    return df


if __name__ == "__main__":
    for symbol in SYMBOLS:
        df = build_features(symbol)
        if not df.empty:
            indicator_cols = [c for c in df.columns if c not in
                              {"_id", "symbol", "interval", "open_time", "close_time",
                               "open", "high", "low", "close", "volume",
                               "quote_asset_volume", "number_of_trades",
                               "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume",
                               "ignore"}]
            print(f"\n{symbol}: {df.shape[0]} rows — indicators: {indicator_cols}")
            print(df[["open_time", "close"] + indicator_cols[:4]].tail(3).to_string(index=False))
