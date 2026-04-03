# 🐳 Guide Docker - Stack complète

## Vue d'ensemble

La stack Docker complète inclut **6 services** :

| Service | Port | Container | Description |
|---------|------|-----------|-------------|
| **MongoDB** | 27025 | `sep25_opa1_mongo` | Base de données NoSQL pour les données crypto |
| **PostgreSQL** | 5435 | `sep25_opa1_postgres` | Base de données relationnelle |
| **PgAdmin** | 5436 | `sep25_opa1_pgadmin4` | Interface web pour PostgreSQL |
| **API FastAPI** | 8000 | `sep25_opa1_api` | API REST + WebSocket |
| **Dashboard Dash** | 8050 | `sep25_opa1_dashboard` | Interface web de visualisation |
| **Scheduler** | — | `sep25_opa1_scheduler` | Collecte quotidienne des données Binance |

---

## 🚀 Démarrage rapide

### Tout démarrer en une commande

```bash
# Linux / WSL
./start_stack.sh

# Windows
start_stack.bat
```

Cette commande :
1. ✅ Vérifie que Docker est lancé
2. ✅ Crée le fichier `.env` si nécessaire
3. ✅ Demande si vous voulez peupler les données
4. ✅ Build les images Docker
5. ✅ Démarre tous les services
6. ✅ Attend que tout soit healthy

---

## 📦 Services détaillés

### 1. MongoDB (mongo)
```yaml
Port: 27025
Container: sep25_opa1_mongo
Image: mongo:7.0
```

**Données stockées** :
- `historical_daily_data` : Données historiques
- `streaming_trades` : Trades en temps réel

**Accès** :
```bash
# Via mongosh
docker exec -it sep25_opa1_mongo mongosh -u root -p password

# Via Python
from pymongo import MongoClient
client = MongoClient("mongodb://root:password@localhost:27025/")
```

### 2. PostgreSQL (postgres)
```yaml
Port: 5435
Container: sep25_opa1_postgres
Image: postgres:latest
```

**Tables** :
- Métadonnées système
- Configuration
- Utilisateurs (à venir)

### 3. PgAdmin (pgadmin)
```yaml
Port: 5436
Container: sep25_opa1_pgadmin4
URL: http://localhost:5436
```

**Connexion** :
- Email : `admin@admin.com` (configurable dans `.env`)
- Password : défini dans `.env`

### 4. API FastAPI (api)
```yaml
Port: 8000
Container: sep25_opa1_api
Build: Dockerfile
```

**Endpoints principaux** :
- `GET /health` - Health check
- `GET /api/symbols` - Liste des cryptos
- `GET /api/historical` - Données historiques
- `WS /ws/stream/{symbol}` - Stream temps réel

**Documentation** : http://localhost:8000/docs

### 5. Dashboard Dash (dashboard)
```yaml
Port: 8050
Container: sep25_opa1_dashboard
Build: Dockerfile.dashboard
```

**Fonctionnalités** :
- 📈 Graphiques interactifs (candlestick)
- 📊 Volumes de trading
- 📉 Indicateurs techniques (RSI, MA7, MA30)
- ⚡ Prix en temps réel via API Binance (ticker 24h, heure Paris)

**URL** : http://localhost:8050

### 6. Scheduler (scheduler) 🆕
```yaml
Port: —  (pas de port exposé)
Container: sep25_opa1_scheduler
Build: Dockerfile.scheduler
```

**Rôle** : Collecte automatique des données Binance et upsert dans MongoDB.

**Comportement** :
- Collecte **immédiatement au démarrage** (rattrapage)
- Puis **chaque jour à 01:00 UTC** (02h/03h heure de Paris)
- Couvre les **2 dernières années** pour BTCUSDT, ETHUSDT, SOLUSDT
- Upsert → **aucun doublon** dans MongoDB

**Variable de configuration** :

| Variable | Défaut | Description |
|---|---|---|
| `COLLECT_TIME` | `01:00` | Heure de collecte HH:MM (UTC) |

> ⚠️ Ce scheduler sera remplacé par **Apache Airflow** dans une phase ultérieure.

---

## 🔧 Commandes utiles

### Gestion des services

```bash
# Démarrer tous les services
docker-compose up -d

# Démarrer un service spécifique
docker-compose up -d dashboard

# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes (⚠️ perte de données)
docker-compose down -v

# Redémarrer un service
docker-compose restart api
docker-compose restart dashboard
```

### Logs

```bash
# Logs de tous les services
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f api
docker-compose logs -f dashboard
docker-compose logs -f scheduler   # Collecte automatique

# Dernières 100 lignes
docker-compose logs --tail=100 dashboard
docker-compose logs --tail=50 scheduler

# Logs depuis un temps donné
docker-compose logs --since 30m dashboard
```

### Build et rebuild

```bash
# Rebuild tous les services
docker-compose build

# Rebuild un service spécifique
docker-compose build dashboard

# Rebuild et redémarrer
docker-compose up -d --build dashboard

# Rebuild sans cache
docker-compose build --no-cache dashboard
```

### État des services

```bash
# Liste des containers
docker-compose ps

# État détaillé
docker ps --filter name=sep25_opa1

# Utilisation des ressources
docker stats

# Inspecter un service
docker inspect sep25_opa1_dashboard
```

### Accès aux containers

```bash
# Shell dans un container
docker exec -it sep25_opa1_api bash
docker exec -it sep25_opa1_dashboard bash

# Exécuter une commande
docker exec sep25_opa1_api python -c "import dash; print(dash.__version__)"

# Accès MongoDB
docker exec -it sep25_opa1_mongo mongosh
```

---

## 🔍 Debugging

### Dashboard ne démarre pas

```bash
# Vérifier les logs
docker-compose logs dashboard

# Vérifier que l'API est accessible
docker exec sep25_opa1_dashboard curl http://api:8000/health

# Rebuild le dashboard
docker-compose build --no-cache dashboard
docker-compose up -d dashboard
```

### API ne répond pas

```bash
# Vérifier les logs
docker-compose logs api

# Vérifier MongoDB
docker exec sep25_opa1_api python -c "from pymongo import MongoClient; print(MongoClient('mongodb://mongo:27017/').server_info())"

# Restart l'API
docker-compose restart api
```

### Scheduler ne collecte pas

```bash
# Vérifier les logs du scheduler
docker-compose logs scheduler

# Vérifier que MongoDB est accessible depuis le scheduler
docker exec sep25_opa1_scheduler python -c "
import os
from pymongo import MongoClient
uri = f\"mongodb://{os.environ['MONGO_USER']}:{os.environ['MONGO_PASSWORD']}@{os.environ['MONGO_HOST']}:27017/\"
client = MongoClient(uri, serverSelectionTimeoutMS=3000)
print('Connexion OK :', client[os.environ['MONGO_DB']].list_collection_names())
"

# Forcer une collecte immédiate (redémarrer déclenche la collecte initiale)
docker-compose restart scheduler

# Vérifier le nombre de documents après collecte
docker exec sep25_opa1_mongo mongosh -u sep25opa1 -p sep25opa1 \
  --authenticationDatabase admin \
  --eval "db = db.getSiblingDB('binance_data'); print(db.historical_daily_data.countDocuments({}))"
```

### Problème de connexion entre services

```bash
# Tester la connectivité réseau
docker network inspect sep25_opa1_network

# Ping entre services
docker exec sep25_opa1_dashboard ping api
docker exec sep25_opa1_api ping mongo
```

### Erreur de build

```bash
# Nettoyer les images intermédiaires
docker system prune -f

# Rebuild sans cache
docker-compose build --no-cache

# Supprimer une image spécifique
docker rmi sep25_cde_opa1-dashboard
```

---

## 📊 Health checks

Tous les services ont des health checks :

```bash
# Vérifier la santé de tous les services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Vérifier un service spécifique
docker inspect --format='{{.State.Health.Status}}' sep25_opa1_dashboard

# Attendre qu'un service soit healthy
timeout 60 bash -c 'until docker inspect --format="{{.State.Health.Status}}" sep25_opa1_dashboard | grep -q "healthy"; do sleep 2; done'
```

---

## 🔒 Variables d'environnement

### Fichier .env

```env
# MongoDB
MONGO_USER=root
MONGO_PASSWORD=password
MONGO_DB=crypto_db
MONGO_PORT=27025

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=crypto_db
POSTGRES_PORT=5435

# PgAdmin
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin

# Binance API
URL_HISTORIQUE=https://api.binance.com/api/v3/klines
URL_STREAM=wss://stream.binance.com:9443/ws

# Auto-populate data (true/false)
POPULATE_DATA=false

# Scheduler — heure de collecte quotidienne HH:MM UTC (défaut 01:00 = 02h/03h Paris)
COLLECT_TIME=01:00
```

### Variables spécifiques aux services

| Service | Variable | Valeur |
|---|---|---|
| Dashboard | `API_BASE_URL` | `http://api:8000` (auto) |
| Dashboard | `PYTHONUNBUFFERED` | `1` (auto) |
| Scheduler | `COLLECT_TIME` | `01:00` (configurable) |
| Scheduler | `MONGO_COLLECTION_HISTORICAL` | `historical_daily_data` (auto) |

---

## 📁 Volumes Docker

Les données sont persistées dans des volumes Docker :

```bash
# Lister les volumes
docker volume ls | grep sep25_opa1

# Inspecter un volume
docker volume inspect sep25_cde_opa1_mongo_data

# Backup d'un volume
docker run --rm -v sep25_cde_opa1_mongo_data:/data -v $(pwd):/backup ubuntu tar czf /backup/mongo_backup.tar.gz /data

# Restore d'un volume
docker run --rm -v sep25_cde_opa1_mongo_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/mongo_backup.tar.gz -C /
```

---

## 🌐 Réseau Docker

Les services communiquent via un réseau bridge :

```yaml
networks:
  sep25_opa1_network:
    driver: bridge
```

**Communication interne** :
- Dashboard → API : `http://api:8000`
- Scheduler → MongoDB : `mongodb://mongo:27017`
- API → MongoDB : `mongodb://mongo:27017`
- API → PostgreSQL : `postgresql://postgres:5432`

**Communication externe** :
- API : `http://localhost:8000`
- Dashboard : `http://localhost:8050`
- Scheduler : pas de port exposé (service interne uniquement)

---

## 🚀 Mode production

Pour déployer en production :

### 1. Créer docker-compose.prod.yml

```yaml
services:
  api:
    environment:
      - POPULATE_DATA=false  # Ne pas peupler en prod
    restart: always
  
  dashboard:
    environment:
      - API_BASE_URL=http://api:8000
    restart: always
```

### 2. Utiliser des secrets

```bash
# Créer des secrets Docker (Docker Swarm)
echo "super_secret_password" | docker secret create mongo_password -
```

### 3. Ajouter un reverse proxy (Nginx)

```nginx
server {
    listen 80;
    server_name crypto-api.example.com;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}

server {
    listen 80;
    server_name crypto-dashboard.example.com;
    
    location / {
        proxy_pass http://localhost:8050;
    }
}
```

### 4. SSL avec Let's Encrypt

```bash
# Installer certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtenir un certificat
sudo certbot --nginx -d crypto-api.example.com
```

---

## 📝 Dockerfile personnalisés

### Dockerfile (API)
```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY run_api.py .
EXPOSE 8000
CMD ["python", "run_api.py"]
```

### Dockerfile.dashboard (Dashboard)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY run_dashboard.py .
COPY assets/ ./assets/
EXPOSE 8050
CMD ["python", "run_dashboard.py"]
```

### Dockerfile.scheduler (Scheduler)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["python", "-u", "src/data/scheduler.py"]
```

---

## 🎯 Bonnes pratiques

### 1. Sécurité
- ✅ Ne jamais committer de secrets dans Git
- ✅ Utiliser des mots de passe forts
- ✅ Limiter les ports exposés
- ✅ Utiliser des health checks

### 2. Performance
- ✅ Utiliser le cache Docker pour les builds
- ✅ Multi-stage builds pour réduire la taille
- ✅ .dockerignore pour exclure les fichiers inutiles
- ✅ Volumes pour les données persistantes

### 3. Maintenance
- ✅ Logs centralisés
- ✅ Monitoring des ressources
- ✅ Backups réguliers
- ✅ Updates de sécurité

---

## 🆘 Résolution de problèmes

### Erreur "port already allocated"

```bash
# Trouver le processus utilisant le port
lsof -i :8050  # Linux/Mac
netstat -ano | findstr :8050  # Windows

# Changer le port dans docker-compose.yml
ports:
  - "8051:8050"  # Utiliser 8051 au lieu de 8050
```

### Erreur "no space left on device"

```bash
# Nettoyer Docker
docker system prune -a --volumes

# Vérifier l'espace
docker system df
```

### Services ne démarrent pas

```bash
# Vérifier les logs
docker-compose logs

# Recréer les containers
docker-compose down
docker-compose up -d --force-recreate
```

---

## 📚 Ressources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**Dernière mise à jour** : 2026-04-03
**Version Docker** : 24.0+
**Version Docker Compose** : 2.0+

