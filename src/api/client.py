import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class CryptoAPIClient:
  """Client for querying cryptocurrency data from the API."""

  def __init__(self, base_url: str = "http://localhost:8000"):
    """
    Initialize the API client.

    Args:
        base_url: Base URL of the API (default: http://localhost:8000)
    """
    self.base_url = base_url.rstrip('/')
    self.session = requests.Session()

  def health_check(self) -> Dict[str, str]:
    """
    Check if the API is healthy.

    Returns:
        Health status dictionary
    """
    response = self.session.get(f"{self.base_url}/health")
    response.raise_for_status()
    return response.json()

  def get_symbols(self) -> List[str]:
    """
    Get list of available symbols.

    Returns:
        List of symbol strings
    """
    response = self.session.get(f"{self.base_url}/api/symbols")
    response.raise_for_status()
    return response.json()["symbols"]

  def get_intervals(self) -> List[str]:
    """
    Get list of available intervals.

    Returns:
        List of interval strings
    """
    response = self.session.get(f"{self.base_url}/api/intervals")
    response.raise_for_status()
    return response.json()["intervals"]

  def get_historical_data(
          self,
          symbol: str,
          interval: str = "1d",
          start_time: Optional[datetime] = None,
          end_time: Optional[datetime] = None,
          limit: int = 1000
  ) -> List[Dict[str, Any]]:
    """
    Get historical data for a symbol.

    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTCUSDT')
        interval: Time interval (default: '1d')
        start_time: Start datetime (optional)
        end_time: End datetime (optional)
        limit: Maximum number of records (default: 1000)

    Returns:
        List of historical data records
    """
    params = {
      "interval": interval,
      "limit": limit
    }

    if start_time:
      params["start_time"] = start_time.isoformat()
    if end_time:
      params["end_time"] = end_time.isoformat()

    response = self.session.get(
      f"{self.base_url}/api/historical/{symbol}",
      params=params
    )
    response.raise_for_status()
    return response.json()

  def get_latest_data(
          self,
          symbol: str,
          interval: str = "1d",
          count: int = 30
  ) -> List[Dict[str, Any]]:
    """
    Get the most recent data for a symbol.

    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTCUSDT')
        interval: Time interval (default: '1d')
        count: Number of recent records (default: 30)

    Returns:
        List of recent historical data records
    """
    params = {
      "interval": interval,
      "count": count
    }

    response = self.session.get(
      f"{self.base_url}/api/latest/{symbol}",
      params=params
    )
    response.raise_for_status()
    return response.json()

  def get_statistics(
          self,
          symbol: str,
          interval: str = "1d",
          start_time: Optional[datetime] = None,
          end_time: Optional[datetime] = None
  ) -> Dict[str, Any]:
    """
    Get aggregated statistics for a symbol.

    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTCUSDT')
        interval: Time interval (default: '1d')
        start_time: Start datetime (optional)
        end_time: End datetime (optional)

    Returns:
        Dictionary with aggregated statistics
    """
    params = {"interval": interval}

    if start_time:
      params["start_time"] = start_time.isoformat()
    if end_time:
      params["end_time"] = end_time.isoformat()

    response = self.session.get(
      f"{self.base_url}/api/stats/{symbol}",
      params=params
    )
    response.raise_for_status()
    return response.json()

  def get_data_for_period(
          self,
          symbol: str,
          days: int = 30,
          interval: str = "1d"
  ) -> List[Dict[str, Any]]:
    """
    Convenience method to get data for the last N days.

    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTCUSDT')
        days: Number of days to look back (default: 30)
        interval: Time interval (default: '1d')

    Returns:
        List of historical data records
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    return self.get_historical_data(
      symbol=symbol,
      interval=interval,
      start_time=start_time,
      end_time=end_time
    )

  def close(self):
    """Close the session."""
    self.session.close()

  def __enter__(self):
    """Context manager entry."""
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit."""
    self.close()


# Example usage
if __name__ == "__main__":
  # Using context manager
  with CryptoAPIClient() as client:
    # Check health
    health = client.health_check()
    print(f"API Status: {health['status']}")

    # Get available symbols
    symbols = client.get_symbols()
    print(f"\nAvailable symbols: {symbols}")

    # Get last 30 days of BTC data
    print("\nFetching last 30 days of BTCUSDT data...")
    btc_data = client.get_data_for_period("BTCUSDT", days=30)
    print(f"Retrieved {len(btc_data)} records")

    if btc_data:
      latest = btc_data[-1]
      print(f"\nLatest BTC price:")
      print(f"  Time: {latest['open_time']}")
      print(f"  Open: ${latest['open']:,.2f}")
      print(f"  High: ${latest['high']:,.2f}")
      print(f"  Low: ${latest['low']:,.2f}")
      print(f"  Close: ${latest['close']:,.2f}")
      print(f"  Volume: {latest['volume']:,.2f}")

    # Get statistics
    print("\nFetching BTCUSDT statistics...")
    stats = client.get_statistics("BTCUSDT")
    print(f"  Total records: {stats['count']}")
    print(f"  Average close: ${stats['avg_close']:,.2f}")
    print(f"  Min low: ${stats['min_low']:,.2f}")
    print(f"  Max high: ${stats['max_high']:,.2f}")
    print(f"  Total volume: {stats['total_volume']:,.2f}")
