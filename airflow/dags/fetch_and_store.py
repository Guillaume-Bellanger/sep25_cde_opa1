"""
DAG fetch_and_store — collecte quotidienne des données Binance et calcul des features.

Schedule : @daily (minuit UTC)
Tâches   :
  1. fetch_ohlcv     — récupère les chandeliers OHLCV (1h / 4h / 1d) → MongoDB
  2. compute_features — calcule les indicateurs techniques → PostgreSQL
"""
import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Rend src/ accessible : /opt/airflow/src dans le conteneur
sys.path.insert(0, "/opt/airflow")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

default_args = {
    "owner": "cryptobot",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ---------------------------------------------------------------------------
# Callables
# ---------------------------------------------------------------------------

def fetch_ohlcv() -> None:
    """Télécharge 1h / 4h / 1d depuis Binance et upserte dans MongoDB."""
    from src.data.fetch_historical_daily import upsert_all_history
    upsert_all_history()


def compute_and_store_features() -> None:
    """Calcule les indicateurs techniques pour chaque symbole et les stocke dans PostgreSQL."""
    from src.features.build_features import build_features
    from src.data.store_features import store_features
    import logging

    logger = logging.getLogger("airflow.task")
    for symbol in SYMBOLS:
        logger.info(f"Building features for {symbol}")
        df = build_features(symbol)
        if df.empty:
            logger.warning(f"{symbol}: aucune donnée OHLCV — features ignorées")
            continue
        stored = store_features(df, symbol)
        logger.info(f"{symbol}: {stored} lignes stockées dans PostgreSQL")


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

with DAG(
    dag_id="fetch_and_store",
    default_args=default_args,
    description="Collecte OHLCV Binance → MongoDB + calcul features → PostgreSQL",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["crypto", "data", "features"],
) as dag:

    t_fetch = PythonOperator(
        task_id="fetch_ohlcv",
        python_callable=fetch_ohlcv,
    )

    t_features = PythonOperator(
        task_id="compute_features",
        python_callable=compute_and_store_features,
    )

    t_fetch >> t_features
