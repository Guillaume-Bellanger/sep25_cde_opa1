"""FastAPI application for cryptocurrency data API."""
import json
import logging
import pickle
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import sqlalchemy
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.database import Database
from sqlalchemy import text
import asyncio

# Add src/ to sys.path so "from data.xxx" imports resolve
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
  sys.path.insert(0, src_dir)
# Add project root so predict_model internal "from src.data.xxx" imports resolve
project_root = os.path.dirname(src_dir)
if project_root not in sys.path:
  sys.path.insert(0, project_root)

from data.config import SETTINGS
from data.stream_data import BinanceStreamClient
from api.queries import (
  get_symbols,
  get_intervals,
  get_historical_data_query,
  get_latest_data,
  get_aggregated_stats
)
from api.models import (
  HistoricalDataResponse,
  HealthResponse,
  IntervalsResponse,
  ModelMetricsResponse,
  PredictResponse,
  SignalHistoryItem,
  StatsResponse,
  SymbolsResponse,
)

# Configure logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CRYPTO_API")

# Global database connection
mongo_client: Optional[MongoClient] = None
mongo_db: Optional[Database] = None

# Active WebSocket connections
active_streams: dict[str, BinanceStreamClient] = {}
websocket_connections: dict[str, List[WebSocket]] = {}

# ML — PostgreSQL engine + pre-loaded models
pg_engine: Optional[sqlalchemy.engine.Engine] = None
loaded_models: Dict[str, Any] = {}
SYMBOLS_ML = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
SAVED_DIR = Path(__file__).parent.parent.parent / "models" / "saved"


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Lifespan context manager for database connections."""
  global mongo_client, mongo_db, pg_engine, loaded_models

  # Startup: Connect to MongoDB
  try:
    db_name = SETTINGS["MONGO_DB"]
    host = SETTINGS["MONGO_HOST"]
    port = int(SETTINGS["MONGO_PORT"])
    user = SETTINGS.get("MONGO_USER", "")
    password = SETTINGS.get("MONGO_PASSWORD", "")

    if user and password:
      mongo_uri = f"mongodb://{user}:{password}@{host}:{port}/"
      mongo_client = MongoClient(mongo_uri)
    else:
      mongo_client = MongoClient(host=host, port=port)

    mongo_db = mongo_client[db_name]

    # Test connection
    mongo_db.list_collection_names()
    logger.info(f"Connected to MongoDB at {host}:{port}, database: {db_name}")

  except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

  # Startup: Connect to PostgreSQL (optional — ML endpoints require it)
  try:
    from data.connector.connector import connect_to_postgres
    pg_engine = connect_to_postgres(
      db_name=SETTINGS["POSTGRES_DB"],
      user=SETTINGS["POSTGRES_USER"],
      password=SETTINGS["POSTGRES_PASSWORD"],
      host=SETTINGS["DB_HOST"],
      port=int(SETTINGS["POSTGRES_PORT"]),
    )
    with pg_engine.connect() as conn:
      conn.execute(text("SELECT 1"))
    logger.info("Connected to PostgreSQL")
  except Exception as e:
    logger.warning(f"PostgreSQL unavailable — ML endpoints will return 503: {e}")
    pg_engine = None

  # Startup: Pre-load ML models from disk
  for sym in SYMBOLS_ML:
    pkl_path = SAVED_DIR / sym / "model.pkl"
    if pkl_path.exists():
      try:
        with open(pkl_path, "rb") as f:
          loaded_models[sym] = pickle.load(f)
        logger.info(f"ML model loaded for {sym}")
      except Exception as e:
        logger.warning(f"Could not load model for {sym}: {e}")

  yield

  # Shutdown: Close streams and MongoDB connection
  for stream in active_streams.values():
    stream.stop()

  if pg_engine:
    pg_engine.dispose()
    logger.info("Closed PostgreSQL connection")

  if mongo_client:
    mongo_client.close()
    logger.info("Closed MongoDB connection")


# Create FastAPI app
app = FastAPI(
  title="Cryptocurrency Data API",
  description="API to query historical cryptocurrency data from MongoDB",
  version="1.0.0",
  lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
  """Root endpoint."""
  return {
    "status": "ok",
    "message": "Cryptocurrency Data API is running"
  }


@app.get("/health", response_model=HealthResponse)
async def health_check():
  """Health check endpoint."""
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    # Test database connection
    mongo_db.list_collection_names()

    return {
      "status": "healthy",
      "message": "All services are operational",
      "model_loaded": len(loaded_models) > 0,
    }
  except Exception as e:
    logger.error(f"Health check failed: {e}")
    raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/api/symbols", response_model=SymbolsResponse)
async def get_available_symbols():
  """Get list of available cryptocurrency symbols."""
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    symbols = get_symbols(mongo_db)
    return {"symbols": symbols}

  except Exception as e:
    logger.error(f"Error fetching symbols: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching symbols: {str(e)}")


@app.get("/api/intervals", response_model=IntervalsResponse)
async def get_available_intervals():
  """Get list of available time intervals."""
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    intervals = get_intervals(mongo_db)
    return {"intervals": intervals}

  except Exception as e:
    logger.error(f"Error fetching intervals: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching intervals: {str(e)}")


@app.get("/api/historical/{symbol}", response_model=List[HistoricalDataResponse])
async def get_historical_data(
        symbol: str,
        interval: str = Query("1d", description="Time interval (e.g., '1d', '1h')"),
        start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
        end_time: Optional[str] = Query(None, description="End time (ISO format)"),
        limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records")
):
  """
  Get historical data for a specific symbol.

  - **symbol**: Cryptocurrency symbol (e.g., BTCUSDT)
  - **interval**: Time interval (default: 1d)
  - **start_time**: Start time in ISO format (optional)
  - **end_time**: End time in ISO format (optional)
  - **limit**: Maximum number of records to return (default: 1000, max: 10000)
  """
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    # Parse datetime strings if provided
    start_dt = None
    end_dt = None

    if start_time:
      try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format.")

    if end_time:
      try:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format.")

    # Query data
    data = get_historical_data_query(
      db=mongo_db,
      symbol=symbol,
      interval=interval,
      start_time=start_dt,
      end_time=end_dt,
      limit=limit
    )

    if not data:
      raise HTTPException(
        status_code=404,
        detail=f"No data found for symbol {symbol} with interval {interval}"
      )

    return data

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Error fetching historical data: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")


@app.get("/api/latest/{symbol}", response_model=List[HistoricalDataResponse])
async def get_latest(
        symbol: str,
        interval: str = Query("1d", description="Time interval (e.g., '1d', '1h')"),
        count: int = Query(30, ge=1, le=365, description="Number of recent records")
):
  """
  Get the most recent data for a specific symbol.

  - **symbol**: Cryptocurrency symbol (e.g., BTCUSDT)
  - **interval**: Time interval (default: 1d)
  - **count**: Number of recent records to return (default: 30, max: 365)
  """
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    data = get_latest_data(
      db=mongo_db,
      symbol=symbol,
      interval=interval,
      count=count
    )

    if not data:
      raise HTTPException(
        status_code=404,
        detail=f"No data found for symbol {symbol} with interval {interval}"
      )

    return data

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Error fetching latest data: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")


@app.get("/api/stats/{symbol}", response_model=StatsResponse)
async def get_statistics(
        symbol: str,
        interval: str = Query("1d", description="Time interval (e.g., '1d', '1h')"),
        start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
        end_time: Optional[str] = Query(None, description="End time (ISO format)")
):
  """
  Get aggregated statistics for a specific symbol.

  - **symbol**: Cryptocurrency symbol (e.g., BTCUSDT)
  - **interval**: Time interval (default: 1d)
  - **start_time**: Start time in ISO format (optional)
  - **end_time**: End time in ISO format (optional)
  """
  try:
    if mongo_db is None:
      raise HTTPException(status_code=503, detail="Database not connected")

    # Parse datetime strings if provided
    start_dt = None
    end_dt = None

    if start_time:
      try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format.")

    if end_time:
      try:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
      except ValueError:
        raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format.")

    # Get statistics
    stats = get_aggregated_stats(
      db=mongo_db,
      symbol=symbol,
      interval=interval,
      start_time=start_dt,
      end_time=end_dt
    )

    if stats.get("count", 0) == 0:
      raise HTTPException(
        status_code=404,
        detail=f"No data found for symbol {symbol} with interval {interval}"
      )

    return stats

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Error fetching statistics: {e}")
    raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


def _save_prediction(result: Dict[str, Any]) -> None:
  """Persist a prediction to the predictions table (best-effort, non-blocking)."""
  if pg_engine is None:
    return
  try:
    with pg_engine.begin() as conn:
      conn.execute(
        text("""
          INSERT INTO predictions (timestamp, symbol, signal, signal_label, confidence, model_version)
          VALUES (:timestamp, :symbol, :signal, :signal_label, :confidence, :model_version)
        """),
        {
          "timestamp": result["timestamp"],
          "symbol": result["symbol"],
          "signal": int(result["signal"]),
          "signal_label": result["signal_label"],
          "confidence": float(result["confidence"]),
          "model_version": result["model_version"],
        },
      )
  except Exception as e:
    logger.warning(f"Could not save prediction to DB: {e}")


@app.get("/predict", response_model=PredictResponse)
async def predict_signal(
  symbol: str = Query("BTCUSDT", description="Symbol: BTCUSDT, ETHUSDT or SOLUSDT"),
):
  """Generate a BUY / SELL / HOLD signal for the latest candle of a symbol."""
  symbol = symbol.upper()
  if symbol not in loaded_models:
    raise HTTPException(status_code=404, detail=f"No model for {symbol}. Run train_model first.")
  if pg_engine is None:
    raise HTTPException(status_code=503, detail="PostgreSQL unavailable — cannot fetch latest features.")
  try:
    from models.predict_model import predict
    result = predict(symbol)
    _save_prediction(result)
    return result
  except (FileNotFoundError, ValueError) as e:
    raise HTTPException(status_code=404, detail=str(e))
  except Exception as e:
    logger.error(f"/predict error for {symbol}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/features")
async def get_features(
  symbol: str = Query("BTCUSDT", description="Symbol: BTCUSDT, ETHUSDT or SOLUSDT"),
  limit: int = Query(100, ge=1, le=1000, description="Number of rows (most recent first)"),
) -> List[Dict[str, Any]]:
  """Return the latest feature rows for a symbol from PostgreSQL."""
  symbol = symbol.upper()
  if pg_engine is None:
    raise HTTPException(status_code=503, detail="PostgreSQL unavailable.")
  try:
    df = pd.read_sql(
      text("SELECT * FROM features WHERE symbol = :symbol ORDER BY timestamp DESC LIMIT :limit"),
      pg_engine,
      params={"symbol": symbol, "limit": limit},
    )
    if df.empty:
      raise HTTPException(status_code=404, detail=f"No features found for {symbol}.")
    df = df.sort_values("timestamp").reset_index(drop=True)
    for col in df.select_dtypes(include=["datetimetz", "datetime64[ns, UTC]", "datetime64[ns]"]).columns:
      df[col] = df[col].astype(str)
    return df.to_dict(orient="records")
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"/features error for {symbol}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/signal/history", response_model=List[SignalHistoryItem])
async def get_signal_history(
  symbol: str = Query("BTCUSDT", description="Symbol: BTCUSDT, ETHUSDT or SOLUSDT"),
  limit: int = Query(50, ge=1, le=500, description="Number of past signals to return"),
) -> List[SignalHistoryItem]:
  """Return the last N predictions for a symbol from the predictions table."""
  symbol = symbol.upper()
  if pg_engine is None:
    raise HTTPException(status_code=503, detail="PostgreSQL unavailable.")
  try:
    df = pd.read_sql(
      text("SELECT * FROM predictions WHERE symbol = :symbol ORDER BY timestamp DESC LIMIT :limit"),
      pg_engine,
      params={"symbol": symbol, "limit": limit},
    )
    if df.empty:
      raise HTTPException(status_code=404, detail=f"No signal history for {symbol}.")
    for col in df.select_dtypes(include=["datetimetz", "datetime64[ns, UTC]", "datetime64[ns]"]).columns:
      df[col] = df[col].astype(str)
    return df.to_dict(orient="records")
  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"/signal/history error for {symbol}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/model/metrics", response_model=List[ModelMetricsResponse])
async def get_model_metrics(
  symbol: Optional[str] = Query(None, description="Filter by symbol (omit for all)"),
) -> List[ModelMetricsResponse]:
  """Return training metrics for saved models (read from metrics.json files on disk)."""
  targets = [symbol.upper()] if symbol else SYMBOLS_ML
  results: List[ModelMetricsResponse] = []
  for sym in targets:
    json_path = SAVED_DIR / sym / "metrics.json"
    if json_path.exists():
      try:
        with open(json_path) as f:
          m = json.load(f)
        results.append(ModelMetricsResponse(
          symbol=m["symbol"],
          model_name=m["model_name"],
          model_version=m["model_version"],
          date_train=m["date_train"],
          accuracy=m["accuracy"],
          f1_macro=m["f1_macro"],
          sharpe_ratio=m["sharpe_ratio"],
          n_train=m["n_train"],
          n_val=m["n_val"],
          n_test=m["n_test"],
        ))
      except Exception as e:
        logger.warning(f"Could not load metrics for {sym}: {e}")
  if not results:
    raise HTTPException(status_code=404, detail="No metrics found for the requested symbol(s).")
  return results


@app.websocket("/ws/stream/{symbol}")
async def websocket_stream(websocket: WebSocket, symbol: str):
  """
  WebSocket endpoint pour recevoir les données de trading en temps réel.

  - **symbol**: Symbole de crypto (ex: BTCUSDT)

  Example (JavaScript):
      const ws = new WebSocket('ws://localhost:8000/ws/stream/BTCUSDT');
      ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          console.log(`${data.symbol}: $${data.price}`);
      };
  """
  await websocket.accept()
  symbol_upper = symbol.upper()

  logger.info(f"WebSocket client connected for {symbol_upper}")

  # Ajouter cette connexion à la liste
  if symbol_upper not in websocket_connections:
    websocket_connections[symbol_upper] = []
  websocket_connections[symbol_upper].append(websocket)

  # Stocker le loop de l'événement pour pouvoir y accéder depuis le thread
  loop = asyncio.get_event_loop()

  try:
    # Démarrer un stream si ce n'est pas déjà fait pour ce symbole
    if symbol_upper not in active_streams:
      def broadcast_trade(trade_data):
        """Broadcast les données à tous les clients WebSocket connectés."""
        if symbol_upper in websocket_connections:
          # Utiliser run_coroutine_threadsafe pour appeler la coroutine depuis un thread
          asyncio.run_coroutine_threadsafe(
            send_to_all_clients(symbol_upper, trade_data),
            loop
          )

      stream_client = BinanceStreamClient(
        symbols=[symbol],
        db=mongo_db,
        callback=broadcast_trade
      )
      stream_client.start()
      active_streams[symbol_upper] = stream_client
      logger.info(f"Started new stream for {symbol_upper}")

    # Garder la connexion ouverte
    while True:
      # Attendre des messages du client (principalement pour détecter la déconnexion)
      try:
        data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        # On peut gérer des commandes du client ici si nécessaire
        if data == "ping":
          await websocket.send_json({"type": "pong"})
      except asyncio.TimeoutError:
        # Timeout normal, continuer
        continue

  except WebSocketDisconnect:
    logger.info(f"WebSocket client disconnected for {symbol_upper}")
  except Exception as e:
    logger.error(f"WebSocket error for {symbol_upper}: {e}")
  finally:
    # Retirer cette connexion de la liste
    if symbol_upper in websocket_connections:
      websocket_connections[symbol_upper].remove(websocket)

      # Si plus aucune connexion pour ce symbole, arrêter le stream
      if not websocket_connections[symbol_upper]:
        if symbol_upper in active_streams:
          active_streams[symbol_upper].stop()
          del active_streams[symbol_upper]
          logger.info(f"Stopped stream for {symbol_upper} (no more clients)")
        del websocket_connections[symbol_upper]


async def send_to_all_clients(symbol: str, trade_data: dict):
  """
  Envoie les données de trade à tous les clients WebSocket connectés pour un symbole.

  Args:
      symbol: Symbole de crypto
      trade_data: Données du trade
  """
  if symbol not in websocket_connections:
    return

  # Préparer le message
  message = {
    "symbol": trade_data["symbol"],
    "price": trade_data["price"],
    "quantity": trade_data["quantity"],
    "timestamp": trade_data["timestamp"].isoformat(),
    "trade_id": trade_data["trade_id"],
    "is_buyer_maker": trade_data["is_buyer_maker"]
  }

  # Envoyer à tous les clients
  disconnected = []
  for ws in websocket_connections[symbol]:
    try:
      await ws.send_json(message)
    except Exception as e:
      logger.error(f"Error sending to client: {e}")
      disconnected.append(ws)

  # Retirer les connexions qui ont échoué
  for ws in disconnected:
    websocket_connections[symbol].remove(ws)


@app.get("/api/stream/active")
async def get_active_streams():
  """
  Obtenir la liste des streams actifs.

  Returns:
      Liste des symboles avec streams actifs et nombre de clients connectés
  """
  return {
    "active_streams": [
      {
        "symbol": symbol,
        "connected_clients": len(websocket_connections.get(symbol, []))
      }
      for symbol in active_streams.keys()
    ]
  }


if __name__ == "__main__":
  import uvicorn

  uvicorn.run(app, host="0.0.0.0", port=8000)
