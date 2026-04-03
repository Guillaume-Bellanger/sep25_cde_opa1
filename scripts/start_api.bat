@echo off
REM Script pour démarrer rapidement l'API (Windows)

echo ==========================================
echo    Démarrage de l'API Cryptocurrency
echo ==========================================
echo.

REM Vérifier que Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python n'est pas installé
    pause
    exit /b 1
)

REM Vérifier que les dépendances sont installées
echo Vérification des dépendances...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo ! FastAPI n'est pas installé
    echo Installation des dépendances...
    pip install -r requirements.txt
)

REM Vérifier que le fichier .env existe
if not exist .env (
    echo ! Fichier .env non trouvé
    echo Création d'un fichier .env depuis .env.example...
    copy .env.example .env
    echo + Fichier .env créé. Veuillez le configurer avant de relancer.
    pause
    exit /b 1
)

echo.
echo Démarrage de l'API sur http://localhost:8000
echo Documentation disponible sur http://localhost:8000/docs
echo.
echo Appuyez sur Ctrl+C pour arrêter...
echo.

REM Démarrer l'API
python run_api.py

pause

