"""Vérifie que les imports clés du projet fonctionnent sans erreur."""
import pytest


def test_import_settings():
    """data.config.SETTINGS est importable et est un dict."""
    from data.config import SETTINGS
    assert isinstance(SETTINGS, dict)
    assert SETTINGS["MONGO_DB"] is not None


def test_import_api_models():
    """api.models contient les modèles Pydantic attendus."""
    from api.models import HealthResponse, SymbolsResponse, PredictResponse
    assert HealthResponse is not None
    assert SymbolsResponse is not None
    assert PredictResponse is not None


def test_import_api_queries():
    """api.queries expose les fonctions de requête."""
    from api.queries import get_symbols, get_intervals, get_latest_data
    assert callable(get_symbols)
    assert callable(get_intervals)
    assert callable(get_latest_data)


def test_import_fastapi_app():
    """L'application FastAPI est instanciée avec le bon titre."""
    pytest.importorskip("fastapi", reason="fastapi non installé — skip en dehors du venv CI")
    from api.app import app
    assert app.title == "Cryptocurrency Data API"
    assert app.version == "1.0.0"
