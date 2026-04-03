SEP25_CDE_OPA_GROUPE_1
==============================

## Définition du projet

De nos jours, le monde des crypto commence à prendre une place importante et grossit. Il s'agit tout simplement de
marchés financiers assez volatiles et instables se basant sur la technologie de la Blockchain.

Le but de ce projet est de créer un bot de trading, basé sur un modèle de Machine Learning, qui investira sur des
marchés crypto.

## Etapes

- ✅ Récupération des données via l'API Binance
    - ✅ Données historiques, pour l'entraînement des modèles
    - ✅ Stockage dans MongoDB
    - ✅ API REST pour interroger les données
    - ✅ Données en temps réel (streaming WebSocket)
- ✅ Dashboard interactif avec Dash
    - ✅ Graphiques de prix (candlestick)
    - ✅ Indicateurs techniques (RSI, moyennes mobiles)
    - ✅ Prix en temps réel via API Binance
- ⏳ Exploration et analyse des données
- ⏳ Préparation des données
- ⏳ Entraînement de modèles de Machine Learning
- ⏳ Évaluation des modèles
- ⏳ Déploiement du bot de trading

## Architecture technique

### Base de données

- **PostgreSQL** : Métadonnées et configuration
- **MongoDB** : Données historiques et trades de cryptomonnaies

### Déploiement

#### Option 1 : Docker (Recommandé)

Démarrer toute la stack en une commande :

```bash
# Linux / Mac / WSL
./start_stack.sh

# Windows
start_stack.bat
```

Cette commande démarre automatiquement :

| Service    | Port  | URL                        |
|------------|-------|----------------------------|
| 🐳 MongoDB  | 27025 | mongodb://localhost:27025  |
| 🐘 PostgreSQL | 5435 | postgresql://localhost:5435 |
| 🔧 PgAdmin  | 5436  | http://localhost:5436      |
| 🚀 API FastAPI | 8000 | http://localhost:8000   |
| 📊 Dashboard Dash | 8050 | http://localhost:8050 |
| 🕐 Scheduler | —   | collecte quotidienne 01h UTC |

#### Option 2 : Installation locale

**Prérequis** : Python ≥ 3.12

1. Installer les dépendances :

```bash
pip install -r requirements.txt
```

2. Configurer le fichier `.env` (voir `.env.example`)

**Variables importantes** :
- `MONGO_HOST`, `MONGO_PORT`, `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_DB`
- `MONGO_COLLECTION_HISTORICAL` : Collection données historiques (défaut: `historical_daily_data`)
- `MONGO_COLLECTION_STREAMING` : Collection trades temps réel (défaut: `streaming_trades`)

3. Initialiser PostgreSQL :

```bash
python init_database.py
```

4. Lancer l'API puis le dashboard :

```bash
python run_api.py        # http://localhost:8000
python run_dashboard.py  # http://localhost:8050
```

### API REST

Une API FastAPI permet d'interroger les données historiques stockées dans MongoDB.

#### Documentation interactive

- Swagger UI : `http://localhost:8000/docs`
- Référence complète : [references/API_DOCUMENTATION.md](references/API_DOCUMENTATION.md)

#### Endpoints

**REST** :
- `GET /health` — Health check
- `GET /api/symbols` — Symboles disponibles
- `GET /api/intervals` — Intervalles disponibles
- `GET /api/historical/{symbol}` — Données historiques (params : `interval`, `start_time`, `end_time`, `limit`)
- `GET /api/latest/{symbol}` — Dernières données
- `GET /api/stats/{symbol}` — Statistiques agrégées

**WebSocket** :
- `WS /ws/stream/{symbol}` — Trades en temps réel
- `GET /api/stream/active` — Streams actifs

#### Collecte de données en streaming

```python
from src.data.stream_data import stream_trades

def on_trade(data):
    print(f"{data['symbol']}: ${data['price']}")

stream_trades(['BTCUSDT'], duration_seconds=30, callback=on_trade)
```

```javascript
// Depuis un navigateur
const ws = new WebSocket('ws://localhost:8000/ws/stream/BTCUSDT');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`${data.symbol}: $${data.price}`);
};
```

### 📊 Dashboard interactif

Un dashboard Dash permet de visualiser les données de manière interactive.

**Stack technique** :
- Dash 4.0.0
- dash-bootstrap-components 2.0.4 (thème DARKLY)
- plotly 6.5.2

#### Fonctionnalités

- 📈 **Graphique des prix** : Chandelier japonais (candlestick) avec zoom et pan
- 📊 **Volumes de trading** : Code couleur vert/rouge
- 📉 **Indicateurs techniques** : RSI (14), MA7, MA30
- 💰 **Statistiques historiques** : Prix, variation, volume, max/min sur la période
- ⚡ **Prix en temps réel** : Ticker live Binance (rafraîchissement toutes les 3 s), heure Paris
- 🔄 **Actualisation** : Manuelle ou automatique

#### Démarrage standalone

```bash
./scripts/start_dashboard.sh   # Linux/WSL
scripts\start_dashboard.bat    # Windows
python run_dashboard.py        # Manuel
```

### 🕐 Scheduler de collecte automatique

Un service dédié collecte automatiquement les données Binance et les stocke dans MongoDB via upsert quotidien.

**Comportement** :
- Une collecte est lancée **immédiatement au démarrage** du container (initialisation / rattrapage)
- Puis **chaque jour à 01:00 UTC** (02h/03h heure de Paris selon l'heure d'été)
- Les données sont insérées en **upsert** (pas de doublons)
- Couvre les **2 dernières années** de chandeliers journaliers pour BTCUSDT, ETHUSDT, SOLUSDT

**Configuration** :

| Variable d'environnement | Défaut | Description |
|---|---|---|
| `COLLECT_TIME` | `01:00` | Heure de collecte HH:MM (UTC) |
| `MONGO_COLLECTION_HISTORICAL` | `historical_daily_data` | Collection cible |

Modifier l'heure dans `.env` :
```dotenv
COLLECT_TIME=02:30   # 02h30 UTC = 03h30/04h30 Paris
```

**Logs** :
```bash
docker-compose logs -f scheduler
```

> ⚠️ **Note** : Ce scheduler basé sur la bibliothèque `schedule` est une solution provisoire.
> Il sera remplacé par **Apache Airflow** dans une phase ultérieure (voir section Optimisations futures).

## Listes des symboles utilisés

- BTCUSDT
- ETHUSDT
- SOLUSDT

## Documentation et liens utiles

- [Documentation Binance API](https://developers.binance.com/docs/binance-spot-api-docs)
- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [Documentation MongoDB](https://docs.mongodb.com/)
- [Documentation Dash](https://dash.plotly.com/)
- [Documentation Docker](https://docs.docker.com/)

## Organisation du projet

```
sep25_cde_opa1/
│
├── assets/                    <- Fichiers statiques servis par Dash
│   └── 10_dash.css            <- CSS personnalisé (animations, scrollbar, switch)
│
├── docs/                      <- Toute la documentation du projet
│   ├── ROADMAP.md             <- Roadmap et prochaines étapes
│   ├── DASHBOARD_GUIDE.md     <- Guide d'utilisation du dashboard
│   └── ...
│
├── notebooks/                 <- Jupyter notebooks d'exploration
│
├── references/                <- Dictionnaires de données et documentation API
│   └── API_DOCUMENTATION.md
│
├── reports/
│   └── figures/               <- Graphiques générés
│
├── scripts/                   <- Scripts utilitaires (démarrage, validation)
│   ├── start_dashboard.sh/.bat   <- Démarrage dashboard seul
│   ├── start_api.sh/.bat         <- Démarrage API seule
│   └── validate_docker.sh        <- Validation de la stack Docker│
├── src/                       <- Code source
│   ├── api/                   <- API REST FastAPI
│   │   ├── app.py             <- Application principale (REST + WebSocket)
│   │   ├── models.py          <- Modèles Pydantic (request/response)
│   │   ├── queries.py         <- Requêtes MongoDB
│   │   └── client.py          <- Client API réutilisable
│   │
│   ├── data/                  <- Collecte et accès aux données
│   │   ├── config.py          <- Configuration (variables d'environnement)
│   │   ├── connector/         <- Connecteurs base de données
│   │   ├── fetch_historical_daily.py  <- Récupération historique Binance
│   │   ├── historical_data.py <- Lecture données historiques
│   │   ├── scheduler.py       <- Scheduler de collecte automatique
│   │   └── stream_data.py     <- Streaming WebSocket Binance
│   │
│   ├── features/              <- Feature engineering
│   │   └── build_features.py
│   │
│   ├── models/                <- Modèles ML (à implémenter — Sprint 3)
│   │   ├── train_model.py
│   │   └── predict_model.py
│   │
│   └── visualization/         <- Dashboard Dash
│       ├── dash_app.py        <- Création de l'application Dash
│       ├── layouts.py         <- Composants UI (dbc.Select, graphiques)
│       ├── callbacks.py       <- Callbacks (données historiques + ticker Binance)
│       └── visualize.py       <- Utilitaires de visualisation
│
├── tests/                     <- Tests automatisés et scripts de validation
│   ├── test_dashboard.py
│   ├── test_dashboard_data.py
│   ├── test_imports.py
│   ├── validate_api.py
│   └── integration/
│
├── .env                       <- Variables d'environnement (ne pas committer)
├── .env.example               <- Template des variables d'environnement
├── docker-compose.yml         <- Stack complète (MongoDB, PostgreSQL, API, Dashboard, Scheduler)
├── Dockerfile                 <- Image Docker pour l'API
├── Dockerfile.dashboard       <- Image Docker pour le Dashboard
├── Dockerfile.scheduler       <- Image Docker pour le Scheduler
├── entrypoint.sh              <- Script d'entrée Docker (API)
├── requirements.txt           <- Dépendances Python
├── init_database.py           <- Initialisation PostgreSQL
├── run_api.py                 <- Lancement de l'API FastAPI
├── run_dashboard.py           <- Lancement du Dashboard Dash
├── start_stack.sh / .bat      <- 🔑 Démarrage de toute la stack Docker
└── README.md                  <- Ce fichier
```

## 🔮 Optimisations futures

### Remplacement du Scheduler par Apache Airflow

Le scheduler actuel (`schedule` Python) est une solution simple et fonctionnelle, mais limitée.  
Il sera remplacé par **Apache Airflow** pour bénéficier de :

| Fonctionnalité | `schedule` (actuel) | Apache Airflow (futur) |
|---|---|---|
| Orchestration de DAGs | ❌ | ✅ |
| Interface web de monitoring | ❌ | ✅ |
| Gestion des retries et dépendances | ❌ | ✅ |
| Alertes en cas d'échec | ❌ | ✅ |
| Historique des exécutions | Logs seuls | ✅ BDD dédiée |
| Parallélisme des tâches | ❌ | ✅ |
| Backfill (rattrapage) | Manuel | ✅ Automatique |

**Implémentation prévue** :
```
airflow/
├── dags/
│   └── binance_daily_collect.py  <- DAG de collecte quotidienne
├── docker-compose.airflow.yml    <- Stack Airflow (webserver, scheduler, worker)
└── requirements-airflow.txt
```

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
