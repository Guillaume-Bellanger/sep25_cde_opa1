"""
Scheduler de collecte automatique des données Binance.

Collecte quotidienne des chandeliers journaliers pour tous les symboles
et les stocke (upsert) dans MongoDB.

Note : Ce scheduler à base de cron sera remplacé à terme par Apache Airflow
       pour une meilleure gestion des DAGs, des dépendances et du monitoring.
"""
import logging
import os
import sys
import schedule
import time
from datetime import datetime
from zoneinfo import ZoneInfo

# Assurer que src/ est dans le path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetch_historical_daily import upsert_daily_history

# ─── Configuration ────────────────────────────────────────────────────────────
# Heure de collecte quotidienne (format HH:MM, timezone UTC)
# Modifiable via la variable d'environnement COLLECT_TIME
COLLECT_TIME_UTC = os.environ.get("COLLECT_TIME", "01:00")  # 01h UTC = 02h/03h Paris

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("CRYPTO_SCHEDULER")

PARIS_TZ = ZoneInfo("Europe/Paris")


def run_collection() -> None:
    """Lance la collecte et l'upsert dans MongoDB."""
    now = datetime.now(PARIS_TZ).strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=" * 60)
    logger.info(f"🚀 Collecte automatique démarrée — {now} (heure Paris)")
    logger.info("=" * 60)
    try:
        upsert_daily_history()
        logger.info("✅ Collecte terminée avec succès")
    except Exception as exc:
        logger.error(f"❌ Erreur lors de la collecte : {exc}", exc_info=True)
    logger.info("=" * 60)


def main() -> None:
    logger.info("=" * 60)
    logger.info("🕐 Scheduler de collecte Binance démarré")
    logger.info(f"   Heure de collecte : {COLLECT_TIME_UTC} UTC (quotidienne)")
    logger.info("=" * 60)

    # Collecte immédiate au démarrage (initialisation / rattrapage)
    logger.info("⏳ Collecte initiale au démarrage...")
    run_collection()

    # Programmer la collecte quotidienne
    schedule.every().day.at(COLLECT_TIME_UTC).do(run_collection)
    logger.info(f"📅 Prochaine collecte programmée à {COLLECT_TIME_UTC} UTC")

    # Boucle principale — vérifie toutes les 60 secondes
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()

