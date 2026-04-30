"""
Live prediction service for CryptoBot ML.

Subscribes to Binance kline WebSocket (1m), maintains a rolling window
of closed candles, computes features in-memory, and makes predictions.
"""
import json
import logging
import pickle
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests
import websocket

logger = logging.getLogger("LIVE_PREDICTOR")

SAVED_DIR = Path(__file__).parent.parent.parent / "models" / "saved"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"
WINDOW_SIZE = 350       # rolling window (> SMA_200 + lag_24 warmup)
SIGNAL_NAMES: Dict[int, str] = {1: "BUY", 0: "HOLD", -1: "SELL"}
TARGET_THRESHOLD = 0.001  # 0.1% — threshold for evaluating 1m predictions

# pandas-ta column names → FEATURE_COLS names (must match store_features.COLUMN_MAP)
_RENAME: Dict[str, str] = {
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
}


def _load_model_bundle(symbol: str) -> Dict[str, Any]:
    """Load model bundle; prefers {symbol}_1m, falls back to {symbol}."""
    for variant in [f"{symbol}_1m", symbol]:
        path = SAVED_DIR / variant / "model.pkl"
        if path.exists():
            with open(path, "rb") as f:
                bundle = pickle.load(f)
            logger.info(f"Loaded model variant: {variant}")
            return bundle
    raise FileNotFoundError(
        f"No model found for {symbol}. "
        "Run scripts/retrain_1m.py or src/models/train_model.py first."
    )


def _fetch_initial_klines(symbol: str, n: int = WINDOW_SIZE) -> List[Dict]:
    """Fetch the last n closed 1m klines from Binance REST API."""
    resp = requests.get(
        BINANCE_KLINES_URL,
        params={"symbol": symbol, "interval": "1m", "limit": n},
        timeout=15,
    )
    resp.raise_for_status()
    return [
        {
            "open_time": row[0],
            "open":      float(row[1]),
            "high":      float(row[2]),
            "low":       float(row[3]),
            "close":     float(row[4]),
            "volume":    float(row[5]),
        }
        for row in resp.json()
    ]


def _candles_to_df(candles: List[Dict]) -> pd.DataFrame:
    """Convert list of candle dicts to a properly typed DataFrame."""
    df = pd.DataFrame(candles)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.reset_index(drop=True)


def _compute_feature_row(df: pd.DataFrame, feature_cols: List[str]) -> Optional[pd.Series]:
    """
    Compute all ML features for the last row of df.
    Returns a Series indexed by feature names, or None if not enough data.
    """
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.features.build_features import (
            compute_technical_indicators,
            compute_temporal_features,
            compute_lag_features,
        )
    except ImportError as e:
        logger.error(f"Cannot import feature builders: {e}")
        return None

    try:
        df = compute_technical_indicators(df)
        df = compute_temporal_features(df)
        df = compute_lag_features(df)
        df = df.rename(columns=_RENAME)

        latest = df.iloc[-1]
        missing = [c for c in feature_cols if c not in latest.index or pd.isna(latest[c])]
        if missing:
            logger.debug(f"Skipping — NaN/missing features: {missing[:5]}")
            return None
        return latest
    except Exception as e:
        logger.error(f"Feature computation error: {e}")
        return None


class LivePredictor:
    """
    Real-time prediction service for one crypto symbol.

    Usage::

        predictor = LivePredictor("BTCUSDT")
        predictor.start()          # fetches REST seed + opens WebSocket
        state = predictor.get_state()
        predictor.stop()
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol.upper()
        bundle = _load_model_bundle(self.symbol)
        self.model = bundle["model"]
        self.metrics: Dict[str, Any] = bundle["metrics"]
        self.feature_cols: List[str] = self.metrics["feature_cols"]
        self.label_inv: Dict[int, int] = {
            int(k): int(v) for k, v in self.metrics["label_inv"].items()
        }

        self._candles: deque = deque(maxlen=WINDOW_SIZE)
        self._lock = threading.Lock()

        self.live_price: float = 0.0
        self.live_time: str = ""
        self.current_signal: Optional[Dict] = None
        self.history: List[Dict] = []   # last 20 predictions with evaluation
        self.total: int = 0
        self.correct: int = 0

        self._running: bool = False
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None

    # -----------------------------------------------------------------------
    # Prediction + evaluation
    # -----------------------------------------------------------------------

    def _predict_from_window(self) -> Optional[Dict]:
        with self._lock:
            candles = list(self._candles)
        if len(candles) < 230:
            return None

        df = _candles_to_df(candles)
        row = _compute_feature_row(df, self.feature_cols)
        if row is None:
            return None

        X = pd.DataFrame([row[self.feature_cols].values], columns=self.feature_cols)
        proba = self.model.predict_proba(X)[0]
        pred_idx = int(np.argmax(proba))
        confidence = float(proba[pred_idx])
        signal = self.label_inv[pred_idx]

        return {
            "symbol":          self.symbol,
            "signal":          signal,
            "signal_label":    SIGNAL_NAMES[signal],
            "confidence":      round(confidence, 4),
            "price":           float(row["close"]),
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "model_version":   self.metrics["model_version"],
            "evaluated":       False,
            "correct":         None,
            "actual_ret_pct":  None,
        }

    def _evaluate_last_prediction(self, new_close: float) -> None:
        """Compare the most recent unevaluated prediction against actual price move."""
        if not self.history:
            return
        last = self.history[-1]
        if last.get("evaluated"):
            return
        prev_price = last.get("price", 0.0)
        if prev_price <= 0:
            return

        ret = (new_close - prev_price) / prev_price
        sig = last["signal"]
        correct = (
            (ret >  TARGET_THRESHOLD) if sig ==  1 else
            (ret < -TARGET_THRESHOLD) if sig == -1 else
            (abs(ret) <= TARGET_THRESHOLD)
        )
        last.update({"evaluated": True, "correct": correct, "actual_ret_pct": round(ret * 100, 4)})
        with self._lock:
            self.total += 1
            if correct:
                self.correct += 1
        logger.info(
            f"Eval {last['signal_label']} {'✓' if correct else '✗'} "
            f"(ret={ret*100:.3f}%  score={self.correct}/{self.total})"
        )

    # -----------------------------------------------------------------------
    # WebSocket callbacks
    # -----------------------------------------------------------------------

    def _on_message(self, ws: Any, message: str) -> None:
        try:
            data = json.loads(message)
            kline = data.get("k", {})
            current_close = float(kline.get("c", 0))
            ts_ms = kline.get("T", 0)

            with self._lock:
                self.live_price = current_close
                self.live_time = datetime.fromtimestamp(
                    ts_ms / 1000, tz=timezone.utc
                ).isoformat()

            if kline.get("x"):   # candle closed
                self._evaluate_last_prediction(current_close)
                candle = {
                    "open_time": kline["t"],
                    "open":      float(kline["o"]),
                    "high":      float(kline["h"]),
                    "low":       float(kline["l"]),
                    "close":     float(kline["c"]),
                    "volume":    float(kline["v"]),
                }
                with self._lock:
                    self._candles.append(candle)

                pred = self._predict_from_window()
                if pred:
                    with self._lock:
                        self.current_signal = pred
                        self.history.append(pred)
                        if len(self.history) > 20:
                            self.history.pop(0)
                    logger.info(
                        f"Signal {pred['signal_label']} @ {pred['price']:.2f} "
                        f"conf={pred['confidence']:.1%}"
                    )
        except Exception as e:
            logger.error(f"WS message error: {e}")

    def _on_error(self, ws: Any, error: Any) -> None:
        logger.error(f"WS error: {error}")

    def _on_close(self, ws: Any, code: Any, msg: Any) -> None:
        logger.info(f"WS closed ({code})")
        if self._running:
            time.sleep(5)
            if self._running:
                self._connect()

    def _on_open(self, ws: Any) -> None:
        logger.info(f"Live WS connected: {self.symbol} @kline_1m")

    def _connect(self) -> None:
        url = f"{BINANCE_WS_BASE}/{self.symbol.lower()}@kline_1m"
        try:
            self._ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self._ws.run_forever()
        except Exception as e:
            logger.error(f"WS connection error: {e}")
            if self._running:
                time.sleep(5)
                self._connect()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def start(self) -> None:
        """Seed from REST + open WebSocket in a background thread."""
        if self._running:
            return
        self._running = True
        try:
            candles = _fetch_initial_klines(self.symbol, WINDOW_SIZE)
            with self._lock:
                self._candles.clear()
                self._candles.extend(candles)
            if candles:
                with self._lock:
                    self.live_price = candles[-1]["close"]
            pred = self._predict_from_window()
            if pred:
                with self._lock:
                    self.current_signal = pred
                    self.history.append(pred)
        except Exception as e:
            logger.error(f"Failed to seed initial candles: {e}")

        self._thread = threading.Thread(target=self._connect, daemon=True)
        self._thread.start()
        logger.info(f"LivePredictor started: {self.symbol}")

    def stop(self) -> None:
        """Stop the WebSocket and background thread."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        logger.info(f"LivePredictor stopped: {self.symbol}")

    def get_state(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the current live state."""
        with self._lock:
            score_str = f"{self.correct}/{self.total}" if self.total > 0 else "0/0"
            score_pct = round(self.correct / self.total * 100, 1) if self.total > 0 else None
            return {
                "symbol":              self.symbol,
                "running":             self._running,
                "live_price":          self.live_price,
                "live_time":           self.live_time,
                "signal":              self.current_signal,
                "total_predictions":   self.total,
                "correct_predictions": self.correct,
                "score_pct":           score_pct,
                "score_str":           score_str,
                "history":             list(self.history[-10:]),
            }
