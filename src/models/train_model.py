"""
Training pipeline for CryptoBot ML.

Usage:
    python -m src.models.train_model               # train all symbols
    python -m src.models.train_model --symbol BTCUSDT
"""
import argparse
import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.utils.class_weight import compute_sample_weight
import xgboost as xgb
import lightgbm as lgb

logger = logging.getLogger("CRYPTO_BOT")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
SAVED_DIR = Path(__file__).parent.parent.parent / "models" / "saved"

# Labels fed to models: -1→0, 0→1, 1→2  (XGBoost requires 0-indexed; LightGBM too)
LABEL_MAP: Dict[int, int] = {-1: 0, 0: 1, 1: 2}
LABEL_INV: Dict[int, int] = {0: -1, 1: 0, 2: 1}
SIGNAL_NAMES: Dict[int, str] = {-1: "SELL", 0: "HOLD", 1: "BUY"}

TARGET_THRESHOLD = 0.005   # 0.5 % next-day return → BUY or SELL

FEATURE_COLS: List[str] = [
    "open", "high", "low", "close", "volume",
    "rsi_14", "macd", "macd_hist", "macd_signal",
    "bb_lower", "bb_mid", "bb_upper", "bb_bandwidth", "bb_percent",
    "ema_9", "ema_21", "ema_55",
    "sma_20", "sma_50", "sma_200",
    "atr_14",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "return_1h", "return_4h", "return_24h",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_features(symbol: str) -> pd.DataFrame:
    """Load all feature rows for one symbol from PostgreSQL, sorted by time."""
    from src.data.config import SETTINGS
    from src.data.connector.connector import connect_to_postgres

    engine = connect_to_postgres(
        db_name=SETTINGS["POSTGRES_DB"],
        user=SETTINGS["POSTGRES_USER"],
        password=SETTINGS["POSTGRES_PASSWORD"],
        host=SETTINGS["DB_HOST"],
        port=int(SETTINGS["POSTGRES_PORT"]),
    )
    df = pd.read_sql(
        f"SELECT * FROM features WHERE symbol = '{symbol}' ORDER BY timestamp ASC",
        engine,
    )
    engine.dispose()
    return df


# ---------------------------------------------------------------------------
# Target engineering
# ---------------------------------------------------------------------------

def make_target(close: pd.Series) -> pd.Series:
    """
    Next-period return classification.

    Returns a float Series with NaN on the last row (no future period).
    Values: 1.0 (BUY), -1.0 (SELL), 0.0 (HOLD).
    """
    next_ret = close.shift(-1) / close - 1
    signal = pd.Series(0.0, index=close.index)
    signal[next_ret > TARGET_THRESHOLD] = 1.0
    signal[next_ret < -TARGET_THRESHOLD] = -1.0
    signal[next_ret.isna()] = np.nan   # last row — no label
    return signal


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------

def chronological_split(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """70 % train / 15 % val / 15 % test — strictly chronological, no shuffle."""
    n = len(df)
    i_val = int(n * 0.70)
    i_test = int(n * 0.85)
    return df.iloc[:i_val].copy(), df.iloc[i_val:i_test].copy(), df.iloc[i_test:].copy()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_sharpe(close: pd.Series, predictions: np.ndarray) -> float:
    """
    Annualised Sharpe Ratio of the model's strategy on the test set.

    Long on BUY, short on SELL, flat on HOLD.
    Crypto trades 365 d/year → annualisation factor sqrt(365).
    """
    actual = close.pct_change().shift(-1).fillna(0).values
    strat = np.where(predictions == 1, actual,
            np.where(predictions == -1, -actual, 0.0))
    std = strat.std()
    if std == 0:
        return 0.0
    return float(strat.mean() / std * np.sqrt(365))


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _fit_xgboost(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val: np.ndarray,   y_val: np.ndarray,
    sample_weights: np.ndarray,
) -> xgb.XGBClassifier:
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        early_stopping_rounds=30,
        random_state=42,
        verbosity=0,
    )
    model.fit(
        X_train, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    return model


def _fit_lightgbm(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val: np.ndarray,   y_val: np.ndarray,
    sample_weights: np.ndarray,
) -> lgb.LGBMClassifier:
    model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        num_leaves=31,
        random_state=42,
        verbosity=-1,
    )
    # Fit with DataFrame so LightGBM stores feature names; predict also via DataFrame
    X_tr_df  = pd.DataFrame(X_train, columns=FEATURE_COLS)
    X_val_df = pd.DataFrame(X_val,   columns=FEATURE_COLS)
    model.fit(X_tr_df, y_train, sample_weight=sample_weights,
              eval_set=[(X_val_df, y_val)])
    return model


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def train_symbol(symbol: str) -> Tuple[object, Dict]:
    """
    Full training pipeline for one symbol.

    Returns (best_model, metrics_dict).
    """
    logger.info(f"=== {symbol} ===")

    df = load_features(symbol)
    if df.empty:
        raise ValueError(f"No features in DB for {symbol}")

    df["target"] = make_target(df["close"])
    df = df.dropna(subset=FEATURE_COLS + ["target"]).reset_index(drop=True)
    df["target"] = df["target"].astype(int)

    if len(df) < 100:
        raise ValueError(f"Not enough clean rows for {symbol}: {len(df)}")

    train_df, val_df, test_df = chronological_split(df)
    logger.info(
        f"Split — train:{len(train_df)}  val:{len(val_df)}  test:{len(test_df)}"
    )
    dist = dict(train_df["target"].value_counts().sort_index())
    logger.info(f"Train class dist: {dist}")

    # Remap -1/0/1  →  0/1/2
    X_tr  = train_df[FEATURE_COLS].values
    y_tr  = np.array([LABEL_MAP[v] for v in train_df["target"]])
    X_val = val_df[FEATURE_COLS].values
    y_val = np.array([LABEL_MAP[v] for v in val_df["target"]])
    X_te  = test_df[FEATURE_COLS].values
    y_te  = np.array([LABEL_MAP[v] for v in test_df["target"]])

    sw = compute_sample_weight("balanced", y_tr)

    # --- XGBoost ---
    xgb_m = _fit_xgboost(X_tr, y_tr, X_val, y_val, sw)
    xgb_pred = xgb_m.predict(X_te)
    xgb_orig = np.array([LABEL_INV[p] for p in xgb_pred])
    y_te_orig = np.array([LABEL_INV[p] for p in y_te])

    xgb_acc    = accuracy_score(y_te_orig, xgb_orig)
    xgb_f1     = f1_score(y_te_orig, xgb_orig, average="macro", zero_division=0)
    xgb_sharpe = compute_sharpe(test_df["close"].reset_index(drop=True), xgb_orig)
    logger.info(f"XGBoost  acc={xgb_acc:.3f}  f1={xgb_f1:.3f}  sharpe={xgb_sharpe:.3f}")

    # --- LightGBM ---
    lgb_m = _fit_lightgbm(X_tr, y_tr, X_val, y_val, sw)
    X_te_df = pd.DataFrame(X_te, columns=FEATURE_COLS)
    lgb_pred = lgb_m.predict(X_te_df)
    lgb_orig = np.array([LABEL_INV[p] for p in lgb_pred])

    lgb_acc    = accuracy_score(y_te_orig, lgb_orig)
    lgb_f1     = f1_score(y_te_orig, lgb_orig, average="macro", zero_division=0)
    lgb_sharpe = compute_sharpe(test_df["close"].reset_index(drop=True), lgb_orig)
    logger.info(f"LightGBM acc={lgb_acc:.3f}  f1={lgb_f1:.3f}  sharpe={lgb_sharpe:.3f}")

    # Pick best by F1 macro on test
    if xgb_f1 >= lgb_f1:
        best_name, best_model = "xgboost", xgb_m
        best_acc, best_f1, best_sharpe = xgb_acc, xgb_f1, xgb_sharpe
    else:
        best_name, best_model = "lightgbm", lgb_m
        best_acc, best_f1, best_sharpe = lgb_acc, lgb_f1, lgb_sharpe

    logger.info(f"Winner: {best_name}  f1={best_f1:.3f}  sharpe={best_sharpe:.3f}")

    model_version = (
        f"{symbol}_{best_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )

    metrics = {
        "symbol": symbol,
        "model_name": best_name,
        "model_version": model_version,
        "date_train": datetime.now(timezone.utc).isoformat(),
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "accuracy": round(best_acc, 4),
        "f1_macro": round(best_f1, 4),
        "sharpe_ratio": round(best_sharpe, 4),
        "threshold": TARGET_THRESHOLD,
        "feature_cols": FEATURE_COLS,
        "label_map": LABEL_MAP,
        "label_inv": LABEL_INV,
        "all_models": {
            "xgboost":  {"accuracy": round(xgb_acc, 4), "f1_macro": round(xgb_f1, 4), "sharpe": round(xgb_sharpe, 4)},
            "lightgbm": {"accuracy": round(lgb_acc, 4), "f1_macro": round(lgb_f1, 4), "sharpe": round(lgb_sharpe, 4)},
        },
    }

    return best_model, metrics


def save_model(model: object, metrics: Dict, symbol: str) -> Path:
    """Persist model + metrics under models/saved/<symbol>/."""
    save_dir = SAVED_DIR / symbol
    save_dir.mkdir(parents=True, exist_ok=True)

    pkl_path = save_dir / "model.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({"model": model, "metrics": metrics}, f)

    json_path = save_dir / "metrics.json"
    with open(json_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    logger.info(f"Saved {pkl_path}")
    logger.info(f"Saved {json_path}")
    return save_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CryptoBot ML models")
    parser.add_argument("--symbol", default=None, help="Single symbol (default: all)")
    args = parser.parse_args()

    targets = [args.symbol] if args.symbol else SYMBOLS
    for sym in targets:
        try:
            model, metrics = train_symbol(sym)
            save_model(model, metrics, sym)
            print(
                f"\n{sym}: acc={metrics['accuracy']}  "
                f"f1={metrics['f1_macro']}  sharpe={metrics['sharpe_ratio']}"
            )
        except Exception as e:
            logger.error(f"{sym}: training failed — {e}")
