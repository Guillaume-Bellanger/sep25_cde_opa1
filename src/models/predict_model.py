"""
Prediction module for CryptoBot ML.

Usage:
    python -m src.models.predict_model BTCUSDT
    python -m src.models.predict_model          # defaults to BTCUSDT
"""
import argparse
import logging
import pickle
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("CRYPTO_BOT")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

SAVED_DIR = Path(__file__).parent.parent.parent / "models" / "saved"
SIGNAL_NAMES: Dict[int, str] = {1: "BUY", 0: "HOLD", -1: "SELL"}


def load_model(symbol: str) -> tuple:
    """Load (model, metrics) from models/saved/<symbol>/model.pkl."""
    path = SAVED_DIR / symbol / "model.pkl"
    if not path.exists():
        raise FileNotFoundError(
            f"No model for {symbol} at {path}. Run train_model first."
        )
    with open(path, "rb") as f:
        bundle = pickle.load(f)
    return bundle["model"], bundle["metrics"]


def get_latest_features(symbol: str, feature_cols: list) -> pd.DataFrame:
    """Fetch the most recent feature row for a symbol from PostgreSQL."""
    from src.data.config import SETTINGS
    from src.data.connector.connector import connect_to_postgres

    engine = connect_to_postgres(
        db_name=SETTINGS["POSTGRES_DB"],
        user=SETTINGS["POSTGRES_USER"],
        password=SETTINGS["POSTGRES_PASSWORD"],
        host=SETTINGS["DB_HOST"],
        port=int(SETTINGS["POSTGRES_PORT"]),
    )
    # "close" is already in feature_cols; only add "timestamp" for display
    extra = ['"timestamp"']
    cols_sql = ", ".join([f'"{c}"' for c in feature_cols] + extra)
    query = (
        f"SELECT {cols_sql} FROM features "
        f"WHERE symbol = '{symbol}' ORDER BY timestamp DESC LIMIT 1"
    )
    df = pd.read_sql(query, engine)
    engine.dispose()
    return df


def predict(symbol: str) -> Dict:
    """
    Generate a BUY / SELL / HOLD signal for the latest candle of a symbol.

    Returns a dict with keys:
      symbol, signal, signal_label, confidence, price, timestamp, model_version.
    """
    model, metrics = load_model(symbol)
    feature_cols: list = metrics["feature_cols"]
    label_inv: Dict = {int(k): int(v) for k, v in metrics["label_inv"].items()}

    df = get_latest_features(symbol, feature_cols)
    if df.empty:
        raise ValueError(f"No feature rows found in DB for {symbol}")

    # Keep as DataFrame so LightGBM models receive named features (avoids sklearn warning)
    X = df[feature_cols]
    proba = model.predict_proba(X)[0]           # shape (3,): p(class_0), p(class_1), p(class_2)
    pred_idx = int(np.argmax(proba))
    confidence = float(proba[pred_idx])

    # label_inv maps model class index → original signal (-1 / 0 / 1)
    signal = label_inv[pred_idx]

    return {
        "symbol": symbol,
        "signal": signal,
        "signal_label": SIGNAL_NAMES[signal],
        "confidence": round(confidence, 4),
        "price": float(df["close"].iloc[0]),
        "timestamp": str(df["timestamp"].iloc[0]),
        "model_version": metrics["model_version"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict BUY/SELL/HOLD for a symbol")
    parser.add_argument("symbol", nargs="?", default="BTCUSDT")
    args = parser.parse_args()

    result = predict(args.symbol)
    width = 42
    print(f"\n{'='*width}")
    print(f"  Symbol    : {result['symbol']}")
    print(f"  Price     : {result['price']:>12,.2f} USDT")
    print(f"  Signal    : {result['signal_label']}  ({result['signal']:+d})")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  Timestamp : {result['timestamp']}")
    print(f"  Model     : {result['model_version']}")
    print(f"{'='*width}\n")
