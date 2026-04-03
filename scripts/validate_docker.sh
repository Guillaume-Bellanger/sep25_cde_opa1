#!/bin/bash
# Script de validation de la configuration Docker

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Validation de la configuration Docker                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success=0
warnings=0
errors=0

# Check Docker
echo "1. Vérification de Docker..."
if command -v docker &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Docker est installé"
    docker_version=$(docker --version)
    echo "    Version: $docker_version"
    ((success++))
else
    echo -e "  ${RED}✗${NC} Docker n'est pas installé"
    ((errors++))
fi

# Check Docker Compose
echo ""
echo "2. Vérification de Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Docker Compose est installé"
    compose_version=$(docker-compose --version)
    echo "    Version: $compose_version"
    ((success++))
else
    echo -e "  ${RED}✗${NC} Docker Compose n'est pas installé"
    ((errors++))
fi

# Check docker-compose.yml
echo ""
echo "3. Validation du fichier docker-compose.yml..."
if [ -f "docker-compose.yml" ]; then
    echo -e "  ${GREEN}✓${NC} docker-compose.yml existe"

    # Validate syntax
    if docker-compose config > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Syntaxe du docker-compose.yml valide"
        ((success++))
    else
        echo -e "  ${RED}✗${NC} Erreur de syntaxe dans docker-compose.yml"
        docker-compose config
        ((errors++))
    fi
else
    echo -e "  ${RED}✗${NC} docker-compose.yml n'existe pas"
    ((errors++))
fi

# Check Dockerfiles
echo ""
echo "4. Vérification des Dockerfiles..."

if [ -f "Dockerfile" ]; then
    echo -e "  ${GREEN}✓${NC} Dockerfile (API) existe"
    ((success++))
else
    echo -e "  ${RED}✗${NC} Dockerfile (API) manquant"
    ((errors++))
fi

if [ -f "Dockerfile.dashboard" ]; then
    echo -e "  ${GREEN}✓${NC} Dockerfile.dashboard existe"
    ((success++))
else
    echo -e "  ${RED}✗${NC} Dockerfile.dashboard manquant"
    ((errors++))
fi

if [ -f "Dockerfile.scheduler" ]; then
    echo -e "  ${GREEN}✓${NC} Dockerfile.scheduler existe"
    ((success++))
else
    echo -e "  ${RED}✗${NC} Dockerfile.scheduler manquant"
    ((errors++))
fi

# Check .env
echo ""
echo "5. Vérification du fichier .env..."
if [ -f ".env" ]; then
    echo -e "  ${GREEN}✓${NC} .env existe"

    # Check required variables
    required_vars=("MONGO_USER" "MONGO_PASSWORD" "MONGO_DB" "POSTGRES_USER" "POSTGRES_PASSWORD")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Variable $var définie"
        else
            echo -e "  ${YELLOW}⚠${NC} Variable $var non définie"
            ((warnings++))
        fi
    done
    ((success++))
else
    echo -e "  ${YELLOW}⚠${NC} .env n'existe pas (sera créé depuis .env.example)"
    ((warnings++))
fi

# Check required files for dashboard
echo ""
echo "6. Vérification des fichiers du dashboard..."

required_files=(
    "run_dashboard.py"
    "src/visualization/__init__.py"
    "src/visualization/dash_app.py"
    "src/visualization/layouts.py"
    "src/visualization/callbacks.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file existe"
        ((success++))
    else
        echo -e "  ${RED}✗${NC} $file manquant"
        ((errors++))
    fi
done

# Check required files for scheduler
echo ""
echo "7. Vérification des fichiers du scheduler..."

scheduler_files=(
    "src/data/scheduler.py"
    "src/data/fetch_historical_daily.py"
)

for file in "${scheduler_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file existe"
        ((success++))
    else
        echo -e "  ${RED}✗${NC} $file manquant"
        ((errors++))
    fi
done

# Check requirements.txt
echo ""
echo "8. Vérification de requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo -e "  ${GREEN}✓${NC} requirements.txt existe"

    # Check for dashboard dependencies
    if grep -q "dash" requirements.txt; then
        echo -e "  ${GREEN}✓${NC} Dépendance 'dash' présente"
    else
        echo -e "  ${RED}✗${NC} Dépendance 'dash' manquante"
        ((errors++))
    fi

    if grep -q "plotly" requirements.txt; then
        echo -e "  ${GREEN}✓${NC} Dépendance 'plotly' présente"
    else
        echo -e "  ${RED}✗${NC} Dépendance 'plotly' manquante"
        ((errors++))
    fi

    if grep -q "dash-bootstrap-components" requirements.txt; then
        echo -e "  ${GREEN}✓${NC} Dépendance 'dash-bootstrap-components' présente"
    else
        echo -e "  ${RED}✗${NC} Dépendance 'dash-bootstrap-components' manquante"
        ((errors++))
    fi

    # Check for scheduler dependency
    if grep -q "schedule" requirements.txt; then
        echo -e "  ${GREEN}✓${NC} Dépendance 'schedule' (scheduler) présente"
    else
        echo -e "  ${YELLOW}⚠${NC} Dépendance 'schedule' manquante (requise pour le scheduler)"
        ((warnings++))
    fi

    ((success++))
else
    echo -e "  ${RED}✗${NC} requirements.txt manquant"
    ((errors++))
fi

# Check volumes directories
echo ""
echo "9. Vérification des répertoires..."

for dir in "src" "logs"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} Répertoire $dir existe"
        ((success++))
    else
        echo -e "  ${YELLOW}⚠${NC} Répertoire $dir n'existe pas (sera créé)"
        mkdir -p "$dir"
        ((warnings++))
    fi
done

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                      RÉSUMÉ                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "  ${GREEN}✓${NC} Succès:         $success"
echo -e "  ${YELLOW}⚠${NC} Avertissements: $warnings"
echo -e "  ${RED}✗${NC} Erreurs:        $errors"
echo ""

if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✅ Configuration Docker valide !${NC}"
    echo ""
    echo "Vous pouvez démarrer la stack avec:"
    echo "  ./start_stack.sh"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Des erreurs doivent être corrigées avant de démarrer la stack${NC}"
    echo ""
    exit 1
fi

