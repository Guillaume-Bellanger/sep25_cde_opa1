"""Query functions for MongoDB cryptocurrency data."""
import logging
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from pymongo.collection import Collection

# Add src directory to Python path to allow imports
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
  sys.path.insert(0, src_dir)

from data.config import SETTINGS

logger = logging.getLogger("CRYPTO_API")


def get_symbols(db: Database, collection_name: Optional[str] = None) -> List[str]:
  """
  Get list of available symbols in the database.

  Args:
      db: MongoDB database instance
      collection_name: Name of the collection to query (defaults to SETTINGS value)

  Returns:
      List of unique symbols
  """
  if collection_name is None:
    collection_name = SETTINGS["MONGO_COLLECTION_HISTORICAL"]
  coll: Collection = db[collection_name]
  symbols = coll.distinct("symbol")
  return sorted(symbols)


def get_intervals(db: Database, collection_name: Optional[str] = None) -> List[str]:
  """
  Get list of available intervals in the database.

  Args:
      db: MongoDB database instance
      collection_name: Name of the collection to query (defaults to SETTINGS value)

  Returns:
      List of unique intervals
  """
  if collection_name is None:
    collection_name = SETTINGS["MONGO_COLLECTION_HISTORICAL"]
  coll: Collection = db[collection_name]
  intervals = coll.distinct("interval")
  return sorted(intervals)


def get_historical_data_query(
        db: Database,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        collection_name: Optional[str] = None
) -> List[Dict[str, Any]]:
  """
  Query historical cryptocurrency data from MongoDB.

  Args:
      db: MongoDB database instance
      symbol: Cryptocurrency symbol (e.g., 'BTCUSDT')
      interval: Time interval (e.g., '1d', '1h')
      start_time: Start datetime (UTC)
      end_time: End datetime (UTC)
      limit: Maximum number of records to return
      collection_name: Name of the collection to query (defaults to SETTINGS value)

  Returns:
      List of historical data records
  """
  if collection_name is None:
    collection_name = SETTINGS["MONGO_COLLECTION_HISTORICAL"]
  coll: Collection = db[collection_name]

  # Build query filter
  query_filter = {
    "symbol": symbol,
    "interval": interval
  }

  # Add time range filters
  if start_time or end_time:
    time_filter = {}
    if start_time:
      # Ensure timezone aware
      if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
      time_filter["$gte"] = start_time
    if end_time:
      # Ensure timezone aware
      if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
      time_filter["$lte"] = end_time
    query_filter["open_time"] = time_filter

  # Query and sort by time
  cursor = coll.find(query_filter).sort("open_time", 1).limit(limit)

  # Convert to list and remove MongoDB _id field
  results = []
  for doc in cursor:
    # Remove _id for cleaner JSON output
    if "_id" in doc:
      del doc["_id"]
    # Convert datetime to ISO string for JSON serialization
    if "open_time" in doc and isinstance(doc["open_time"], datetime):
      doc["open_time"] = doc["open_time"].isoformat()
    if "close_time" in doc and isinstance(doc["close_time"], datetime):
      doc["close_time"] = doc["close_time"].isoformat()
    results.append(doc)

  return results


def get_latest_data(
        db: Database,
        symbol: str,
        interval: str = "1d",
        count: int = 30,
        collection_name: Optional[str] = None
) -> List[Dict[str, Any]]:
  """
  Get the most recent N records for a symbol.

  Args:
      db: MongoDB database instance
      symbol: Cryptocurrency symbol (e.g., 'BTCUSDT')
      interval: Time interval (e.g., '1d', '1h')
      count: Number of recent records to return
      collection_name: Name of the collection to query (defaults to SETTINGS value)

  Returns:
      List of recent historical data records
  """
  if collection_name is None:
    collection_name = SETTINGS["MONGO_COLLECTION_HISTORICAL"]
  coll: Collection = db[collection_name]

  query_filter = {
    "symbol": symbol,
    "interval": interval
  }

  # Query and sort by time descending to get latest first
  cursor = coll.find(query_filter).sort("open_time", -1).limit(count)

  # Convert to list and reverse to get chronological order
  results = []
  for doc in cursor:
    if "_id" in doc:
      del doc["_id"]
    if "open_time" in doc and isinstance(doc["open_time"], datetime):
      doc["open_time"] = doc["open_time"].isoformat()
    if "close_time" in doc and isinstance(doc["close_time"], datetime):
      doc["close_time"] = doc["close_time"].isoformat()
    results.append(doc)

  # Reverse to get chronological order
  return list(reversed(results))


def get_aggregated_stats(
        db: Database,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        collection_name: Optional[str] = None
) -> Dict[str, Any]:
  """
  Get aggregated statistics for a symbol over a time range.

  Args:
      db: MongoDB database instance
      symbol: Cryptocurrency symbol (e.g., 'BTCUSDT')
      interval: Time interval (e.g., '1d', '1h')
      start_time: Start datetime (UTC)
      end_time: End datetime (UTC)
      collection_name: Name of the collection to query (defaults to SETTINGS value)

  Returns:
      Dictionary with aggregated statistics
  """
  if collection_name is None:
    collection_name = SETTINGS["MONGO_COLLECTION_HISTORICAL"]
  coll: Collection = db[collection_name]

  # Build match filter
  match_filter = {
    "symbol": symbol,
    "interval": interval
  }

  if start_time or end_time:
    time_filter = {}
    if start_time:
      if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
      time_filter["$gte"] = start_time
    if end_time:
      if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
      time_filter["$lte"] = end_time
    match_filter["open_time"] = time_filter

  # Aggregation pipeline
  pipeline = [
    {"$match": match_filter},
    {
      "$group": {
        "_id": None,
        "count": {"$sum": 1},
        "avg_close": {"$avg": "$close"},
        "min_low": {"$min": "$low"},
        "max_high": {"$max": "$high"},
        "total_volume": {"$sum": "$volume"},
        "first_open_time": {"$min": "$open_time"},
        "last_open_time": {"$max": "$open_time"}
      }
    }
  ]

  result = list(coll.aggregate(pipeline))

  if not result:
    return {
      "symbol": symbol,
      "interval": interval,
      "count": 0
    }

  stats = result[0]
  # Convert datetime to ISO string
  if "first_open_time" in stats and isinstance(stats["first_open_time"], datetime):
    stats["first_open_time"] = stats["first_open_time"].isoformat()
  if "last_open_time" in stats and isinstance(stats["last_open_time"], datetime):
    stats["last_open_time"] = stats["last_open_time"].isoformat()

  # Remove _id and add symbol/interval
  if "_id" in stats:
    del stats["_id"]
  stats["symbol"] = symbol
  stats["interval"] = interval

  return stats
