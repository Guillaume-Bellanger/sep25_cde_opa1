import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Union
from pymongo import UpdateOne
from .connector.connector import connect_to_mongo
from .config import SETTINGS
from .historical_data import get_historical_data

logger = logging.getLogger("CRYPTO_BOT")
logging.basicConfig(level=logging.INFO)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
# Days of history to fetch per interval
INTERVALS: Dict[str, int] = {
    "1h": 30,    # 30 days → 720 candles/symbol
    "4h": 90,   # 90 days → 540 candles/symbol
    "1d": 730,  # 2 years → 730 candles/symbol
}


def to_utc_dt(ts: Union[int, float, str, datetime]) -> datetime:
  """Normalize various timestamp types to UTC datetime."""
  if isinstance(ts, datetime):
    return ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
  if isinstance(ts, (int, float)):
    # Heuristic: ms vs s
    if ts > 10_000_000_000:
      return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
    return datetime.fromtimestamp(ts, tz=timezone.utc)
  # try ISO string
  return datetime.fromisoformat(str(ts)).astimezone(timezone.utc)


def normalize_record(symbol: str, interval: str, item: Any) -> Dict[str, Any]:
  """Map data from get_historical_data to a consistent schema."""
  # Dict-based (preferred)
  if isinstance(item, dict):
    open_time = (
            item.get("open_time")
            or item.get("openTime")
            or item.get("t")
            or item.get("time")
            or item.get("date")
    )
    close_time = item.get("close_time") or item.get("closeTime") or item.get("T")
    doc = {
      "symbol": symbol,
      "interval": interval,
      "open_time": to_utc_dt(open_time),
      "open": float(item.get("open") or item.get("o") or item.get("Open", 0.0)),
      "high": float(item.get("high") or item.get("h") or item.get("High", 0.0)),
      "low": float(item.get("low") or item.get("l") or item.get("Low", 0.0)),
      "close": float(item.get("close") or item.get("c") or item.get("Close", 0.0)),
      "volume": float(item.get("volume") or item.get("v") or item.get("Volume", 0.0)),
    }
    if close_time is not None:
      doc["close_time"] = to_utc_dt(close_time)
    return doc

  # List-based (Binance kline shape)
  if isinstance(item, (list, tuple)) and len(item) >= 6:
    # 0 openTime(ms), 1 open, 2 high, 3 low, 4 close, 5 volume, 6 closeTime(ms)...
    doc = {
      "symbol": symbol,
      "interval": interval,
      "open_time": to_utc_dt(item[0]),
      "open": float(item[1]),
      "high": float(item[2]),
      "low": float(item[3]),
      "close": float(item[4]),
      "volume": float(item[5]),
    }
    if len(item) > 6:
      doc["close_time"] = to_utc_dt(item[6])
    return doc

  raise ValueError("Unsupported record format from get_historical_data")


def _upsert_interval(coll, interval: str, days: int) -> None:
  """Fetch and upsert history for all symbols for a given interval."""
  end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
  start = end - timedelta(days=days)

  for sym in SYMBOLS:
    logger.info(f"Fetching {interval} history for {sym}: {start.isoformat()} → {end.isoformat()}")
    try:
      records = get_historical_data(symbol=sym, interval=interval, start_time=start, end_time=end)
    except Exception as e:
      logger.error(f"API error for {sym} {interval}: {e}")
      continue

    if records.empty:
      logger.warning(f"No data returned for {sym} {interval}")
      continue

    docs: List[Dict[str, Any]] = []
    for _, item in records.iterrows():
      try:
        docs.append(normalize_record(sym, interval, item.to_dict()))
      except Exception as e:
        logger.warning(f"Skip malformed record for {sym} {interval}: {e}")

    if not docs:
      logger.warning(f"No valid documents for {sym} {interval}")
      continue

    ops = [
      UpdateOne(
        {"symbol": d["symbol"], "interval": d["interval"], "open_time": d["open_time"]},
        {"$set": d},
        upsert=True,
      )
      for d in docs
    ]
    result = coll.bulk_write(ops, ordered=False)
    upserts = getattr(result, "upserted_count", 0)
    mods = getattr(result, "modified_count", 0)
    logger.info(f"{sym} {interval}: upserted {upserts}, modified {mods}, total {len(docs)}")


def upsert_all_history() -> None:
  """Fetch and upsert history for all symbols and all configured intervals into MongoDB."""
  db_name = SETTINGS["MONGO_DB"]
  host = SETTINGS["MONGO_HOST"]
  port = int(SETTINGS["MONGO_PORT"])
  user = SETTINGS.get("MONGO_USER", "")
  password = SETTINGS.get("MONGO_PASSWORD", "")
  auth = bool(user)

  client = connect_to_mongo(db_name=db_name, host=host, port=port, auth=auth, user=user, password=password)
  db = client[db_name]
  coll = db[SETTINGS["MONGO_COLLECTION_HISTORICAL"]]
  coll.create_index([("symbol", 1), ("interval", 1), ("open_time", 1)], unique=True)

  for interval, days in INTERVALS.items():
    logger.info(f"=== Interval {interval} ({days} days) ===")
    _upsert_interval(coll, interval, days)

  client.close()


def upsert_daily_history() -> None:
  """Backward-compatible alias — now fetches all intervals."""
  upsert_all_history()
