"""Pydantic models for API request/response validation."""
from typing import Optional, List
from pydantic import BaseModel


class HistoricalDataResponse(BaseModel):
  """Response model for historical data."""
  symbol: str
  interval: str
  open_time: str
  open: float
  high: float
  low: float
  close: float
  volume: float
  close_time: Optional[str] = None


class StatsResponse(BaseModel):
  """Response model for aggregated statistics."""
  symbol: str
  interval: str
  count: int
  avg_close: Optional[float] = None
  min_low: Optional[float] = None
  max_high: Optional[float] = None
  total_volume: Optional[float] = None
  first_open_time: Optional[str] = None
  last_open_time: Optional[str] = None


class SymbolsResponse(BaseModel):
  """Response model for available symbols."""
  symbols: List[str]


class IntervalsResponse(BaseModel):
  """Response model for available intervals."""
  intervals: List[str]


class HealthResponse(BaseModel):
  """Response model for health check."""
  status: str
  message: str
  model_loaded: Optional[bool] = None


# ---------------------------------------------------------------------------
# ML endpoints
# ---------------------------------------------------------------------------

class PredictResponse(BaseModel):
  """BUY/SELL/HOLD prediction for the latest candle."""
  symbol: str
  signal: int
  signal_label: str
  confidence: float
  price: float
  timestamp: str
  model_version: str


class SignalHistoryItem(BaseModel):
  """One row from the predictions table."""
  id: Optional[int] = None
  timestamp: str
  symbol: str
  signal: int
  signal_label: str
  confidence: float
  model_version: Optional[str] = None


class ModelMetricsResponse(BaseModel):
  """Training metrics for one model / symbol."""
  symbol: str
  model_name: str
  model_version: str
  date_train: str
  accuracy: float
  f1_macro: float
  sharpe_ratio: float
  n_train: int
  n_val: int
  n_test: int
