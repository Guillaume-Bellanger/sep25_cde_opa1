@echo off
REM Script de démarrage du dashboard Dash sur Windows
echo =========================================
echo    Demarrage du Crypto Dashboard
echo =========================================
echo.

REM Vérifier si l'environnement virtuel existe
if not exist "venv\" (
    echo Creation de l'environnement virtuel...
    python -m venv venv
)

REM Activer l'environnement virtuel
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Installer les dépendances
echo Installation des dependances...
pip install -r requirements.txt

echo.
echo =========================================
echo Dashboard accessible sur: http://localhost:8050
echo API doit etre sur: http://localhost:8000
echo =========================================
echo.

REM Lancer le dashboard
python run_dashboard.py

pause

