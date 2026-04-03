@echo off
REM Main startup script for the entire cryptocurrency API stack (Windows)

echo ================================================================
echo      Cryptocurrency Data API - Full Stack Deployment
echo ================================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

echo + Docker is running
echo.

REM Check if .env file exists
if not exist .env (
    echo ! .env file not found
    if exist .env.example (
        echo Creating .env from .env.example...
        copy .env.example .env
        echo + .env file created
        echo.
        echo Please review and update the .env file with your settings,
        echo   then run this script again.
        pause
        exit /b 0
    ) else (
        echo No .env.example file found. Cannot create .env
        pause
        exit /b 1
    )
)

echo + .env file exists
echo.

REM Ask if user wants to populate data
echo Do you want to populate historical data on startup?
echo (This will fetch 2 years of data from Binance for BTC, ETH, SOL)
set /p POPULATE="Populate data? (y/N): "
if /i "%POPULATE%"=="y" (
    set POPULATE_DATA=true
    echo + Data will be populated automatically
) else (
    set POPULATE_DATA=false
    echo i Data population skipped (you can run 'python src/main.py' later^)
)

echo.
echo ================================================================
echo Starting services...
echo ================================================================
echo.

REM Stop any existing containers
echo Stopping existing containers...
docker-compose down 2>nul

REM Build and start services
echo.
echo Building and starting services...
echo.
docker-compose up -d --build

echo.
echo ================================================================
echo Waiting for services to be healthy...
echo ================================================================
echo.

REM Wait for services (simple version for Windows)
timeout /t 30 /nobreak >nul

echo.
echo ================================================================
echo Deployment Summary
echo ================================================================
echo.
docker-compose ps
echo.
echo ================================================================
echo + Stack is running!
echo ================================================================
echo.
echo Services available at:
echo   API:              http://localhost:8000
echo   API Docs:         http://localhost:8000/docs
echo   Dashboard:        http://localhost:8050
echo   MongoDB:          localhost:27025
echo   PostgreSQL:       localhost:5435
echo   PgAdmin:          http://localhost:5436
echo.
echo Useful commands:
echo   View logs:           docker-compose logs -f
echo   View API logs:       docker-compose logs -f api
echo   View Dashboard logs: docker-compose logs -f dashboard
echo   Stop all:            docker-compose down
echo   Restart API:         docker-compose restart api
echo   Restart Dashboard:   docker-compose restart dashboard
echo   Restart API:         docker-compose restart api
echo.
echo To populate data manually (if not done automatically^):
echo   docker-compose exec api python src/main.py
echo.
echo ================================================================

pause

