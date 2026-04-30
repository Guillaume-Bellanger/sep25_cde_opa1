# CryptoBot ML — Bot de trading crypto basé sur le Machine Learning

Bot de trading automatisé sur les marchés crypto (BTC, ETH, SOL) utilisant des modèles de Machine Learning entraînés sur des données Binance. Le système couvre l'ensemble du pipeline Data/ML : collecte, feature engineering, entraînement, prédiction temps réel et monitoring.

---

## Sommaire

1. [Description du projet](#description-du-projet)
2. [Architecture](#architecture)
3. [Stack technique](#stack-technique)
4. [Prérequis](#prérequis)
5. [Installation pas à pas](#installation-pas-à-pas)
6. [Lancer les services](#lancer-les-services)
7. [URLs et accès](#urls-et-accès)
8. [Endpoints API](#endpoints-api)
9. [Modèles ML](#modèles-ml)
10. [Démo Live](#démo-live)
11. [Structure du projet](#structure-du-projet)

---

## Description du projet

CryptoBot ML est un système de trading algorithmique complet qui :

- **Collecte** les données OHLCV historiques et en temps réel depuis l'API Binance
- **Calcule** 28 features techniques (RSI, MACD, Bollinger Bands, EMAs, ATR, features temporelles, lags)
- **Entraîne** des modèles XGBoost et LightGBM sur split chronologique strict (70/15/15)
- **Prédit** les signaux BUY / SELL / HOLD avec un score de confiance
- **Affiche** les prédictions en temps réel dans un dashboard Streamlit avec auto-refresh
- **Orchestre** les pipelines de collecte et ré-entraînement via Apache Airflow
- **Monitore** les métriques API et ML avec Prometheus + Grafana

**Cryptos suivies :** BTCUSDT · ETHUSDT · SOLUSDT

**Timeframes disponibles :** 1m (démo live), 1h, 4h, 1d

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Sources de données                          │
│   Binance REST API (OHLCV)        Binance WebSocket (klines live)  │
└───────────────┬─────────────────────────────────┬───────────────────┘
                │                                 │
                ▼                                 ▼
┌───────────────────────────┐      ┌──────────────────────────────────┐
│  Apache Airflow (DAGs)    │      │  LivePredictor (thread interne)   │
│  ├── fetch_and_store      │      │  ├── Seed 350 klines REST         │
│  │   (collecte + features)│      │  ├── WebSocket kline_1m           │
│  └── retrain_model        │      │  ├── Features in-memory           │
│      (ré-entraînement)    │      │  └── Prédiction + score           │
└──────────┬────────────────┘      └───────────────┬──────────────────┘
           │                                       │
           ▼                                       │
┌─────────────────┐   ┌─────────────────┐          │
│    MongoDB      │   │   PostgreSQL    │          │
│  (OHLCV brut)   │   │ features        │          │
│                 │   │ predictions     │          │
│                 │   │ model_metrics   │          │
└────────┬────────┘   └────────┬────────┘          │
         │                     │                   │
         └──────────┬──────────┘                   │
                    ▼                               │
         ┌─────────────────────┐◄──────────────────┘
         │   API FastAPI       │
         │   (port 8001)       │
         │   /predict          │
         │   /features         │
         │   /signal/history   │
         │   /live/start|stop  │
         │   /live/status      │
         │   /metrics (Prom.)  │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐     ┌──────────────────┐
         │  Streamlit (8501)   │     │  Prometheus (9090)│
         │  🔴 Live             │     │  + Grafana (3000) │
         │  📈 Marché           │     │  Latence API      │
         │  🤖 Signaux ML       │     │  Métriques ML     │
         │  📊 Indicateurs      │     └──────────────────┘
         │  ⚙️ Modèle           │
         │  🔍 Monitoring       │
         └─────────────────────┘
```

**Flux principal :**
1. Airflow DAG `fetch_and_store` collecte les klines Binance → MongoDB → features → PostgreSQL
2. Airflow DAG `retrain_model` ré-entraîne le modèle chaque dimanche à 2h
3. L'API FastAPI expose les données et les prédictions ML
4. Le `LivePredictor` (via `/live/start`) ouvre un WebSocket Binance 1m indépendant et prédit en continu
5. Streamlit consomme exclusivement l'API (pas d'accès direct aux BDD)

---

## Stack technique

| Couche | Outil | Version |
|---|---|---|
| Langage | Python | 3.12 |
| Données crypto | Binance API (`python-binance`) | 1.0.33 |
| Data processing | pandas, numpy | 2.x / 1.x |
| Feature engineering | pandas-ta | 0.4.71b0 |
| Machine Learning | scikit-learn, XGBoost, LightGBM | 1.6 / 2.1 / 4.6 |
| API backend | FastAPI + uvicorn | 0.115 / 0.32 |
| Dashboard | Streamlit | ≥1.38 |
| Base de données | MongoDB 7.0 (OHLCV) + PostgreSQL 16 (features/prédictions) | — |
| Orchestration | Apache Airflow (LocalExecutor) | — |
| Monitoring | Prometheus + Grafana | 2.51 / 10.4 |
| Containerisation | Docker + docker-compose | — |
| CI/CD | GitLab CI (`.gitlab-ci.yml`) | — |
| Tests | pytest | — |

---

## Prérequis

- **Docker Desktop** ≥ 24.0 et **docker-compose** ≥ 2.20 ([installer Docker](https://docs.docker.com/get-docker/))
- **4 Go de RAM** disponibles pour Docker (8 Go recommandés avec Airflow)
- Connexion Internet (l'API Binance est publique, aucune clé API requise en lecture)
- Ports libres : 8001, 8501, 8080, 9090, 3000, 27025, 5435, 5436

> Pour lancer uniquement les scripts Python en local (sans Docker), Python ≥ 3.12 est requis.

---

## Installation pas à pas

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd sep25_cde_opa1
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Le fichier `.env` par défaut est fonctionnel sans modification. Voici les variables clés :

```dotenv
# PostgreSQL
POSTGRES_USER=sep25opa1
POSTGRES_PASSWORD=sep25opa1
POSTGRES_DB=binance_data
POSTGRES_PORT=5435          # port exposé sur l'hôte

# PgAdmin
PGADMIN_DEFAULT_EMAIL=user-name@domain-name.com
PGADMIN_DEFAULT_PASSWORD=sep25opa1

# MongoDB
MONGO_USER=sep25opa1
MONGO_PASSWORD=sep25opa1
MONGO_PORT=27025            # port exposé sur l'hôte
MONGO_DB=binance_data
MONGO_COLLECTION_HISTORICAL=historical_daily_data
MONGO_COLLECTION_STREAMING=streaming_trades

# Binance (public, aucune clé requise)
URL_HISTORIQUE=https://api.binance.com/api/v3/klines
URL_STREAM=wss://stream.binance.com:9443/ws/

# Population automatique au premier lancement
POPULATE_DATA=false
```

> Ne jamais committer le fichier `.env` — il est dans `.gitignore`.

### 3. Lancer la stack Docker

```bash
# Linux / macOS / WSL
./start_stack.sh

# Windows (PowerShell ou cmd)
start_stack.bat
```

Cette commande exécute `docker-compose up --build -d` et attend que tous les services soient `healthy`.

> **Premier démarrage :** Airflow effectue une migration de base (~60s) avant que son UI soit disponible.

### 4. Vérifier que tout est opérationnel

```bash
docker-compose ps
```

Tous les services doivent afficher le statut `Up` ou `Up (healthy)`.

---

## Lancer les services

### Stack complète (recommandé)

```bash
docker-compose up -d          # Démarrer en arrière-plan
docker-compose down           # Arrêter
docker-compose logs -f api    # Suivre les logs d'un service
```

### Services individuels

```bash
# API seule (hors Docker)
python run_api.py              # http://localhost:8000

# Streamlit seul (hors Docker)
streamlit run src/visualization/streamlit_app.py
```

### Scripts utilitaires

```bash
# Ré-entraîner le modèle sur 30 jours de klines 1m (toutes les cryptos)
py scripts/retrain_1m.py

# Ré-entraîner sur une crypto et une durée spécifiques
py scripts/retrain_1m.py --symbol BTCUSDT --days 14 --threshold 0.001

# Ré-entraîner sur les données historiques 1h (depuis PostgreSQL)
py -m src.models.train_model

# Calculer et stocker les features dans PostgreSQL
py -m src.data.store_features

# Lancer une prédiction en mode démo (sans base de données)
py -m src.models.predict_model BTCUSDT --demo
```

### Airflow — déclencher un DAG manuellement

```bash
# Depuis l'UI Airflow : http://localhost:8080 (admin / admin)
# Ou en ligne de commande :
docker exec -it sep25_opa1_airflow_webserver airflow dags trigger fetch_and_store
docker exec -it sep25_opa1_airflow_webserver airflow dags trigger retrain_model
```

---

## URLs et accès

| Service | URL | Identifiants |
|---|---|---|
| **Streamlit** — Dashboard principal | http://localhost:8501 | — |
| **API FastAPI** — Swagger UI | http://localhost:8001/docs | — |
| **API FastAPI** — ReDoc | http://localhost:8001/redoc | — |
| **Airflow** — Orchestration DAGs | http://localhost:8080 | `admin` / `admin` |
| **Grafana** — Monitoring | http://localhost:3000 | `admin` / `password` |
| **Prometheus** — Métriques | http://localhost:9090 | — |
| **PgAdmin** — Admin PostgreSQL | http://localhost:5436 | voir `.env` |
| **MongoDB** | `localhost:27025` | voir `.env` |
| **PostgreSQL** | `localhost:5435` | voir `.env` |

---

## Endpoints API

L'API FastAPI est accessible sur `http://localhost:8001`. Documentation interactive : `/docs`.

### Santé et infra

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Statut de l'API et du modèle ML |
| `GET` | `/api/symbols` | Symboles disponibles en base |
| `GET` | `/api/intervals` | Intervalles disponibles |
| `GET` | `/api/stream/active` | Streams WebSocket actifs |
| `GET` | `/metrics` | Métriques Prometheus |

### Données historiques

| Méthode | Endpoint | Paramètres | Description |
|---|---|---|---|
| `GET` | `/api/historical/{symbol}` | `interval`, `limit`, `start_time`, `end_time` | OHLCV depuis MongoDB |
| `GET` | `/api/latest/{symbol}` | `interval`, `count` | Dernières N bougies |
| `GET` | `/api/stats/{symbol}` | `interval`, `start_time`, `end_time` | Statistiques agrégées |

### Machine Learning

| Méthode | Endpoint | Paramètres | Description |
|---|---|---|---|
| `GET` | `/predict` | `symbol` | Signal BUY/SELL/HOLD + confidence (dernière bougie en DB) |
| `GET` | `/features` | `symbol`, `limit` | Features techniques depuis PostgreSQL |
| `GET` | `/signal/history` | `symbol`, `limit` | Historique des prédictions |
| `GET` | `/model/metrics` | `symbol` (optionnel) | Métriques d'entraînement (accuracy, F1, Sharpe) |

### Prédiction Live (WebSocket 1m)

| Méthode | Endpoint | Paramètres | Description |
|---|---|---|---|
| `POST` | `/live/start` | `symbol` | Démarre le LivePredictor (seed REST + WS Binance kline_1m) |
| `POST` | `/live/stop` | `symbol` | Arrête le LivePredictor |
| `GET` | `/live/status` | `symbol` | Prix live, signal courant, score, historique 10 dernières prédictions |

### WebSocket

```
WS ws://localhost:8001/ws/stream/{symbol}
```
Reçoit les trades en temps réel (prix, quantité, timestamp). Exemple JavaScript :

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/stream/BTCUSDT');
ws.onmessage = (e) => {
    const d = JSON.parse(e.data);
    console.log(`${d.symbol}: $${d.price}`);
};
```

### Exemple de réponse `/predict?symbol=BTCUSDT`

```json
{
  "symbol": "BTCUSDT",
  "signal": 1,
  "signal_label": "BUY",
  "confidence": 0.6823,
  "price": 94250.50,
  "timestamp": "2026-04-30T11:00:00+00:00",
  "model_version": "BTCUSDT_xgboost_20260427_084054"
}
```

### Exemple de réponse `/live/status?symbol=BTCUSDT`

```json
{
  "symbol": "BTCUSDT",
  "running": true,
  "live_price": 94312.75,
  "live_time": "2026-04-30T11:03:45+00:00",
  "signal": { "signal_label": "HOLD", "confidence": 0.712, "price": 94310.20 },
  "total_predictions": 15,
  "correct_predictions": 9,
  "score_pct": 60.0,
  "score_str": "9/15",
  "history": [...]
}
```

---

## Modèles ML

### Features (28 colonnes)

| Catégorie | Features |
|---|---|
| OHLCV | `open`, `high`, `low`, `close`, `volume` |
| Momentum | `rsi_14` |
| Tendance | `macd`, `macd_hist`, `macd_signal`, `ema_9`, `ema_21`, `ema_55`, `sma_20`, `sma_50`, `sma_200` |
| Volatilité | `bb_lower`, `bb_mid`, `bb_upper`, `bb_bandwidth`, `bb_percent`, `atr_14` |
| Temporelles | `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos` |
| Lag returns | `return_1h`, `return_4h`, `return_24h` |

### Cible

Signal calculé sur le retour de la bougie suivante :
- **BUY (1)** si retour > seuil
- **SELL (-1)** si retour < -seuil
- **HOLD (0)** sinon

### Split chronologique (no shuffle)

```
|──── 70% train ────|── 15% val ──|── 15% test ──|
       (passé)                         (récent)
```

### Performances (modèles sauvegardés)

| Symbole | Timeframe | Algo | Accuracy | F1 macro | Sharpe |
|---|---|---|---|---|---|
| BTCUSDT | 1h | XGBoost | 0.438 | 0.303 | **2.61** |
| BTCUSDT | 1m | XGBoost | 0.836 | 0.373 | **4.77** |
| ETHUSDT | 1h | XGBoost | — | — | — |
| SOLUSDT | 1h | XGBoost | — | — | — |

> Les modèles `_1m` sont utilisés en priorité par la page **🔴 Live**. Ils sont sauvegardés dans `models/saved/{SYMBOL}_1m/`.

### Ré-entraînement manuel (1m)

```bash
py scripts/retrain_1m.py                   # Toutes les cryptos, 30 jours
py scripts/retrain_1m.py --symbol BTCUSDT  # Une seule crypto
py scripts/retrain_1m.py --days 7          # Sur 7 jours de données
```

### Ré-entraînement automatique (Airflow)

Le DAG `retrain_model` se déclenche **chaque dimanche à 02:00 UTC**. Il peut aussi être déclenché manuellement depuis l'UI Airflow.

---

## Démo Live

La page **🔴 Live** de Streamlit affiche les prédictions du modèle en temps réel :

1. Ouvrir `http://localhost:8501`
2. Sélectionner **🔴 Live** dans la navigation latérale
3. Choisir un symbole (BTCUSDT, ETHUSDT, SOLUSDT)
4. Cliquer **▶ Démarrer**

Le système :
- Charge les 350 dernières bougies 1m depuis l'API Binance REST (seed)
- Ouvre un WebSocket sur le flux `@kline_1m` Binance
- À chaque bougie fermée (toutes les minutes) : calcule les features et génère un signal
- Évalue la prédiction précédente (✅ correcte / ❌ fausse) en comparant le mouvement réel au seuil de 0,1%
- Affiche le score en direct (`correct/total`)
- Auto-refresh toutes les 5 secondes (peut être désactivé)

---

## Structure du projet

```
sep25_cde_opa1/
│
├── airflow/
│   └── dags/
│       ├── fetch_and_store.py     # DAG collecte + features (@daily)
│       └── retrain_model.py       # DAG ré-entraînement (dim. 02h)
│
├── db/
│   └── init_db.sql                # Schéma PostgreSQL (features, predictions, model_metrics)
│
├── docs/                          # Documentation technique
│   ├── DASHBOARD_GUIDE.md
│   └── DOCKER_GUIDE.md
│
├── models/
│   └── saved/
│       ├── BTCUSDT/               # Modèle 1h — model.pkl + metrics.json
│       ├── BTCUSDT_1m/            # Modèle 1m — model.pkl + metrics.json
│       ├── ETHUSDT/
│       ├── ETHUSDT_1m/
│       ├── SOLUSDT/
│       └── SOLUSDT_1m/
│
├── monitoring/
│   ├── prometheus.yml             # Config scraping Prometheus
│   └── grafana/
│       └── provisioning/          # Dashboards + datasources Grafana auto-provisionnés
│
├── scripts/
│   ├── retrain_1m.py              # Ré-entraînement standalone sur données 1m Binance
│   ├── start_api.sh/.bat          # Lancement API seule
│   ├── start_dashboard.sh/.bat    # Lancement Streamlit seul
│   └── validate_docker.sh         # Validation stack Docker
│
├── src/
│   ├── api/
│   │   ├── app.py                 # FastAPI — REST + WebSocket + endpoints Live
│   │   ├── models.py              # Modèles Pydantic (request/response)
│   │   └── queries.py             # Requêtes MongoDB
│   │
│   ├── data/
│   │   ├── config.py              # Variables d'environnement (SETTINGS)
│   │   ├── connector/connector.py # Connecteurs MongoDB + PostgreSQL
│   │   ├── stream_data.py         # BinanceStreamClient (trades WebSocket)
│   │   ├── store_features.py      # Upsert features → PostgreSQL
│   │   └── fetch_klines_binance.py
│   │
│   ├── features/
│   │   └── build_features.py      # compute_technical_indicators / temporal / lag
│   │
│   ├── models/
│   │   ├── train_model.py         # Pipeline entraînement 1h (depuis PostgreSQL)
│   │   ├── predict_model.py       # Prédiction depuis DB + mode démo
│   │   └── live_predictor.py      # LivePredictor — WebSocket 1m + score temps réel
│   │
│   └── visualization/
│       └── streamlit_app.py       # Dashboard Streamlit (6 pages)
│
├── tests/
│   ├── conftest.py
│   └── integration/
│
├── .env                           # Variables d'environnement (ne pas committer)
├── .env.example                   # Template
├── .gitlab-ci.yml                 # Pipeline CI/CD (lint → test → build → deploy)
├── docker-compose.yml             # Stack complète (11 services)
├── Dockerfile                     # Image API FastAPI
├── Dockerfile.airflow             # Image Apache Airflow
├── Dockerfile.streamlit           # Image Streamlit
├── requirements.txt               # Dépendances API + ML
├── requirements.streamlit.txt     # Dépendances Streamlit
├── init_database.py               # Init PostgreSQL (hors Docker)
├── run_api.py                     # Lancement API (hors Docker)
├── start_stack.sh / start_stack.bat  # Démarrage stack Docker
└── README.md                      # Ce fichier
```

---

## Pipeline CI/CD

Le fichier `.gitlab-ci.yml` définit 4 stages :

| Stage | Action |
|---|---|
| `lint` | `ruff` sur `src/` |
| `test` | `pytest tests/ -v` |
| `build` | Build + push des images Docker vers le registre GitLab |
| `deploy` | SSH → `docker-compose pull && up -d` (déclenché manuellement) |

Variables CI requises : `SSH_PRIVATE_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH`, credentials Mongo/Postgres/Binance.

---

## Liens utiles

- [Binance API](https://developers.binance.com/docs/binance-spot-api-docs)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://docs.streamlit.io/)
- [Apache Airflow](https://airflow.apache.org/docs/)
- [XGBoost](https://xgboost.readthedocs.io/)
- [LightGBM](https://lightgbm.readthedocs.io/)
- [Prometheus](https://prometheus.io/docs/)
- [Grafana](https://grafana.com/docs/)

---

<p align="center">
  <small>SEP25_CDE_OPA1 — Groupe 1 · Data Science · 2025-2026</small>
</p>
