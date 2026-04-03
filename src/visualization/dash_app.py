"""
Crypto Dashboard - Application Dash principale
"""
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import logging
import os

logger = logging.getLogger("CRYPTO_DASH")


def create_app():
  """Crée et configure l'application Dash."""

  # Déterminer le chemin racine du projet (2 niveaux au-dessus de ce fichier)
  current_dir = os.path.dirname(os.path.abspath(__file__))
  project_root = os.path.dirname(os.path.dirname(current_dir))

  app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Crypto Dashboard",
    update_title="Mise à jour...",
    assets_folder=os.path.join(project_root, 'assets')  # Chemin absolu vers assets
  )

  # Import du layout après création de l'app
  from visualization.layouts import create_layout
  app.layout = create_layout()

  # Import et enregistrement des callbacks
  from visualization.callbacks import register_callbacks
  register_callbacks(app)

  logger.info("Dash application créée avec succès")

  return app


if __name__ == "__main__":
  # Configuration du logging
  logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  )

  app = create_app()
  app.run(debug=True, host="0.0.0.0", port=8050)
