#!/bin/bash
# Script pour démarrer rapidement l'API

echo "=========================================="
echo "   Démarrage de l'API Cryptocurrency    "
echo "=========================================="
echo ""

# Vérifier que Python est installé
if ! command -v python3 &> /dev/null; then
    echo "Python3 n'est pas installé"
    exit 1
fi

# Vérifier que les dépendances sont installées
echo "🔍 Vérification des dépendances..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "FastAPI n'est pas installé"
    echo "Installation des dépendances..."
    pip install -r requirements.txt
fi

# Vérifier que le fichier .env existe
if [ ! -f .env ]; then
    echo "Fichier .env non trouvé"
    echo "Création d'un fichier .env depuis .env.example..."
    cp .env.example .env
    echo "Fichier .env créé. Veuillez le configurer avant de relancer."
    exit 1
fi

echo ""
echo "Démarrage de l'API sur http://localhost:8000"
echo "Documentation disponible sur http://localhost:8000/docs"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter..."
echo ""

# Démarrer l'API
python3 run_api.py

