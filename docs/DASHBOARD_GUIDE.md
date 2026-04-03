# 📊 Dashboard Dash - Guide d'utilisation

## Vue d'ensemble

Le dashboard Dash est une interface web interactive pour visualiser et analyser les données de cryptomonnaies en temps réel. Il offre :

- 📈 **Graphiques interactifs** : Prix, volumes, indicateurs techniques
- 🔄 **Actualisation automatique** : Rafraîchissement des données en temps réel
- 🎨 **Interface moderne** : Design dark mode avec Bootstrap
- 📊 **Indicateurs techniques** : RSI, moyennes mobiles, etc.
- 💰 **Statistiques en direct** : Prix actuel, variation 24h, volumes

## 🚀 Démarrage rapide

### Prérequis

1. **API FastAPI** doit être lancée sur `http://localhost:8000`
2. **MongoDB** avec des données historiques
3. **Python 3.8+** installé

### Lancement

**Sur Windows :**
```bash
start_dashboard.bat
```

**Sur Linux/WSL :**
```bash
chmod +x start_dashboard.sh
./start_dashboard.sh
```

**Ou manuellement :**
```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le dashboard
python run_dashboard.py
```

### Accès

Une fois lancé, ouvrez votre navigateur à l'adresse :
```
http://localhost:8050
```

## 📱 Fonctionnalités

### 1. Sélection de cryptomonnaie

Utilisez le menu déroulant pour choisir parmi les cryptos disponibles :
- BTCUSDT (Bitcoin)
- ETHUSDT (Ethereum)
- Et plus encore...

### 2. Période d'analyse

Choisissez la période à visualiser :
- 24 heures
- 7 jours
- 30 jours
- 90 jours
- 1 an

### 3. Intervalle de temps

Sélectionnez la granularité des données :
- 1m, 5m, 15m, 30m (minutes)
- 1h, 4h, 12h (heures)
- 1d, 1w, 1M (jours, semaines, mois)

### 4. Cartes de statistiques

En haut du dashboard, 4 cartes affichent :
- 💰 **Prix actuel** : Dernier prix de clôture
- 📈 **Variation 24h** : Pourcentage de changement
- 📊 **Volume 24h** : Volume de trading total
- 🎯 **Max / Min** : Prix maximum et minimum

### 5. Graphique des prix

Affiche un chandelier japonais (candlestick) avec :
- Prix d'ouverture, fermeture, max, min
- Moyenne mobile 7 jours (orange)
- Moyenne mobile 30 jours (violet)
- Navigation interactive (zoom, pan)

### 6. Graphique des volumes

Barre chart des volumes de trading :
- Vert : Prix à la hausse (close > open)
- Rouge : Prix à la baisse (close < open)

### 7. Indicateurs techniques

**RSI (Relative Strength Index)** :
- Ligne orange : Valeur du RSI
- Ligne rouge (70) : Zone de surachat
- Ligne verte (30) : Zone de survente

**Interprétation** :
- RSI > 70 : Suracheté (possibilité de correction)
- RSI < 30 : Survendu (possibilité de rebond)

### 8. Streaming temps réel (en développement)

Active le flux de données en temps réel via WebSocket Binance.

## 🎨 Personnalisation

### Modifier les couleurs

Éditez `src/visualization/layouts.py` pour changer le thème :
```python
external_stylesheets=[dbc.themes.DARKLY]  # Changez DARKLY par FLATLY, SOLAR, etc.
```

### Ajouter des indicateurs

Dans `src/visualization/callbacks.py`, ajoutez vos propres calculs :
```python
# Exemple : Ajouter MACD
df['ema12'] = df['close'].ewm(span=12).mean()
df['ema26'] = df['close'].ewm(span=26).mean()
df['macd'] = df['ema12'] - df['ema26']
```

### Modifier le rafraîchissement auto

Dans `src/visualization/layouts.py` :
```python
dcc.Interval(
    id='auto-refresh-interval',
    interval=60*1000,  # Changez 60 pour autre chose (en ms)
    ...
)
```

## 📁 Architecture

```
src/visualization/
├── __init__.py              # Module exports
├── dash_app.py              # Application Dash principale
├── layouts.py               # Définition des layouts
├── callbacks.py             # Logique des callbacks
└── visualize.py             # (Legacy, non utilisé)

run_dashboard.py             # Script de lancement
start_dashboard.sh/.bat      # Scripts de démarrage
```

## 🔧 Développement

### Mode debug

Le dashboard est lancé en mode debug par défaut :
```python
app.run(debug=True, dev_tools_hot_reload=True)
```

Cela permet :
- Rechargement automatique du code
- Messages d'erreur détaillés
- Console de debug dans le navigateur

### Ajouter un nouveau graphique

1. **Dans `layouts.py`**, ajoutez un nouvel élément :
```python
dcc.Graph(id='new-chart')
```

2. **Dans `callbacks.py`**, créez le callback :
```python
@app.callback(
    Output('new-chart', 'figure'),
    Input('historical-data-store', 'data')
)
def update_new_chart(data):
    # Votre logique ici
    return fig
```

### Tester les callbacks

```python
# Dans callbacks.py, ajoutez des logs
logger.info(f"Données reçues : {len(data)} points")
```

## 🐛 Dépannage

### Dashboard ne démarre pas

**Erreur : Port 8050 déjà utilisé**
```bash
# Trouver et tuer le processus
lsof -ti:8050 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :8050   # Windows
```

**Erreur : Module non trouvé**
```bash
pip install -r requirements.txt --force-reinstall
```

### Pas de données affichées

1. Vérifiez que l'API est lancée :
```bash
curl http://localhost:8000/health
```

2. Vérifiez les logs du dashboard :
```
Erreur lors de la mise à jour des données: ...
```

3. Testez l'API manuellement :
```bash
curl "http://localhost:8000/api/historical?symbol=BTCUSDT&interval=1d"
```

### Graphiques vides

- Assurez-vous que MongoDB contient des données
- Vérifiez la période sélectionnée (peut-être trop récente)
- Regardez les logs de l'API pour les erreurs

## 📊 Améliorations futures

- [ ] WebSocket temps réel intégré
- [ ] Comparaison multi-cryptos
- [ ] Alertes de prix
- [ ] Export CSV/Excel
- [ ] Annotation sur les graphiques
- [ ] Stratégies de trading
- [ ] Prédictions ML
- [ ] Mode clair/sombre toggle
- [ ] Multi-langues

## 🔗 Liens utiles

- [Dash Documentation](https://dash.plotly.com/)
- [Plotly Graphing Library](https://plotly.com/python/)
- [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)
- [API FastAPI](http://localhost:8000/docs)

## 📝 Notes

- Le dashboard utilise **Plotly** pour les graphiques interactifs
- Le thème est **Bootstrap Darkly** pour un look moderne
- Les données sont récupérées via l'API REST FastAPI
- Le rafraîchissement auto peut être désactivé pour économiser des ressources

---

**Auteur** : Projet OPA - Data Engineering
**Dernière mise à jour** : 2026-02-23

