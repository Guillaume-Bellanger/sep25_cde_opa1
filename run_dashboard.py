#!/usr/bin/env python3
"""
Script pour démarrer le dashboard Dash
"""
import sys
import os
import logging

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from visualization.dash_app import create_app

if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger("CRYPTO_DASH")

    # Détecter l'environnement (Docker ou local)
    api_url = os.environ.get('API_BASE_URL', 'http://localhost:8000')
    is_docker = os.environ.get('API_BASE_URL') is not None
    debug_mode = not is_docker  # Debug mode uniquement en local

    logger.info("=" * 60)
    logger.info("🚀 Démarrage du Crypto Dashboard")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"🌍 Environnement: {'Docker' if is_docker else 'Local'}")
    logger.info(f"📊 Dashboard accessible sur: http://{'0.0.0.0' if is_docker else 'localhost'}:8050")
    logger.info(f"📡 API FastAPI sur: {api_url}")
    logger.info(f"🔧 Mode debug: {'Activé' if debug_mode else 'Désactivé'}")
    logger.info("")
    logger.info("Appuyez sur Ctrl+C pour arrêter")
    logger.info("=" * 60)

    # Créer et lancer l'application
    app = create_app()
    app.run(
        debug=debug_mode,
        host="0.0.0.0",
        port=8050,
        dev_tools_hot_reload=debug_mode
    )

