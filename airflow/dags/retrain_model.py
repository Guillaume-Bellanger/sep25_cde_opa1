"""
DAG retrain_model — ré-entraînement hebdomadaire des modèles ML.

Schedule : 0 2 * * 0  (dimanche à 02h00 UTC)
Tâche    :
  retrain_all_symbols — charge les features depuis PostgreSQL, entraîne
                        XGBoost et LightGBM, sauvegarde le meilleur modèle.
"""
import sys
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

default_args = {
    "owner": "cryptobot",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


# ---------------------------------------------------------------------------
# Callable
# ---------------------------------------------------------------------------

def retrain_all_symbols() -> None:
    """Ré-entraîne XGBoost + LightGBM pour chaque symbole et sauvegarde le meilleur."""
    from src.models.train_model import train_symbol, save_model

    logger = logging.getLogger("airflow.task")
    for symbol in SYMBOLS:
        logger.info(f"Début entraînement {symbol}")
        try:
            model, metrics = train_symbol(symbol)
            save_path = save_model(model, metrics, symbol)
            logger.info(
                f"{symbol} entraîné — acc={metrics['accuracy']:.4f}  "
                f"f1={metrics['f1_macro']:.4f}  sharpe={metrics['sharpe_ratio']:.4f}  "
                f"→ {save_path}"
            )
        except Exception as exc:
            logger.error(f"{symbol}: entraînement échoué — {exc}")
            raise


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

with DAG(
    dag_id="retrain_model",
    default_args=default_args,
    description="Ré-entraînement hebdomadaire XGBoost/LightGBM (dimanche 02h UTC)",
    schedule="0 2 * * 0",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["crypto", "ml", "training"],
) as dag:

    PythonOperator(
        task_id="retrain_all_symbols",
        python_callable=retrain_all_symbols,
        execution_timeout=timedelta(hours=2),
    )
