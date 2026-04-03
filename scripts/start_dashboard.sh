#!/bin/bash
# Script de démarrage du dashboard Dash sur Linux/WSL

echo "========================================="
echo "   Démarrage du Crypto Dashboard"
echo "========================================="
echo ""

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "Installation des dépendances..."
pip install -r requirements.txt

echo ""
echo "========================================="
echo "Dashboard accessible sur: http://localhost:8050"
echo "API doit être sur: http://localhost:8000"
echo "========================================="
echo ""

# Lancer le dashboard
python run_dashboard.py

