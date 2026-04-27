import logging
from typing import Any, Dict, List

import pandas as pd
import sqlalchemy
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger("CRYPTO_BOT")

TABLE_NAME = "features"

# Map pandas-ta output column names → PostgreSQL column names defined in db/init_db.sql.
# BBands names contain a dot (e.g. BBL_20_2.0) which is invalid in SQL — hence the mapping.
COLUMN_MAP: Dict[str, str] = {
    "open_time":      "timestamp",
    "open":           "open",
    "high":           "high",
    "low":            "low",
    "close":          "close",
    "volume":         "volume",
    # Technical indicators
    "RSI_14":         "rsi_14",
    "MACD_12_26_9":   "macd",
    "MACDh_12_26_9":  "macd_hist",
    "MACDs_12_26_9":  "macd_signal",
    "BBL_20_2.0_2.0": "bb_lower",
    "BBM_20_2.0_2.0": "bb_mid",
    "BBU_20_2.0_2.0": "bb_upper",
    "BBB_20_2.0_2.0": "bb_bandwidth",
    "BBP_20_2.0_2.0": "bb_percent",
    "EMA_9":          "ema_9",
    "EMA_21":         "ema_21",
    "EMA_55":         "ema_55",
    "SMA_20":         "sma_20",
    "SMA_50":         "sma_50",
    "SMA_200":        "sma_200",
    "ATRr_14":        "atr_14",
    # Temporal
    "hour":           "hour",
    "day_of_week":    "day_of_week",
    "hour_sin":       "hour_sin",
    "hour_cos":       "hour_cos",
    "dow_sin":        "dow_sin",
    "dow_cos":        "dow_cos",
    # Lag returns
    "return_1h":      "return_1h",
    "return_4h":      "return_4h",
    "return_24h":     "return_24h",
}


def _prepare_rows(df: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
    """
    Select, rename and clean DataFrame columns to match the features table schema.

    - Only columns present in both COLUMN_MAP and df are kept.
    - Rows missing timestamp or close are dropped (non-nullable).
    - Remaining NaN are converted to None for SQL NULL compatibility.
    """
    available = {src: dst for src, dst in COLUMN_MAP.items() if src in df.columns}
    sub = df[list(available.keys())].rename(columns=available).copy()
    sub["symbol"] = symbol
    sub = sub.dropna(subset=["timestamp", "close"])
    sub = sub.where(pd.notnull(sub), None)
    return sub.to_dict(orient="records")


def store_features(df: pd.DataFrame, symbol: str) -> int:
    """
    Upsert feature rows for one symbol into the PostgreSQL features table.

    Rows that already exist (same symbol + timestamp) are silently skipped.
    Requires the features table to exist — run db/init_db.sql first.

    Args:
        df:     Enriched DataFrame produced by build_features.build_features().
        symbol: Trading pair symbol (e.g. 'BTCUSDT').

    Returns:
        Number of rows attempted (duplicates not counted by PG on conflict).
    """
    from src.data.config import SETTINGS
    from src.data.connector.connector import connect_to_postgres

    rows = _prepare_rows(df, symbol)
    if not rows:
        logger.warning(f"{symbol}: no rows to store after preparation")
        return 0

    engine = connect_to_postgres(
        db_name=SETTINGS["POSTGRES_DB"],
        user=SETTINGS["POSTGRES_USER"],
        password=SETTINGS["POSTGRES_PASSWORD"],
        host=SETTINGS["DB_HOST"],
        port=int(SETTINGS["POSTGRES_PORT"]),
    )

    try:
        metadata = sqlalchemy.MetaData()
        table = sqlalchemy.Table(TABLE_NAME, metadata, autoload_with=engine)

        stmt = pg_insert(table).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            constraint="features_symbol_timestamp_uq"
        )

        with engine.begin() as conn:
            conn.execute(stmt)

        logger.info(f"{symbol}: {len(rows)} rows upserted into '{TABLE_NAME}'")
        return len(rows)

    except Exception as e:
        logger.error(f"{symbol}: failed to store features — {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    from src.features.build_features import build_features, SYMBOLS

    for symbol in SYMBOLS:
        df = build_features(symbol)
        if not df.empty:
            stored = store_features(df, symbol)
            print(f"{symbol}: {stored} rows stored")
