!/bin/bash
# Entrypoint script for the API container

set -e

echo "================================================"
echo "   Cryptocurrency API - Initialization"
echo "================================================"

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
until python -c "from pymongo import MongoClient; import os; client = MongoClient('mongo', 27017, username=os.getenv('MONGO_USER'), password=os.getenv('MONGO_PASSWORD')); client.admin.command('ping'); print('MongoDB is ready!')" 2>/dev/null; do
  echo "MongoDB is unavailable - sleeping"
  sleep 2
done

echo "✓ MongoDB is ready"

# Wait for PostgreSQL to be ready (optional, for future use)
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d postgres -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "✓ PostgreSQL is ready"

# Create database if it doesn't exist
echo "Initializing PostgreSQL database..."
python init_database.py || echo "Database initialization skipped or failed"

# Check if we should populate data
if [ "$POPULATE_DATA" = "true" ]; then
  echo ""
  echo "================================================"
  echo "   Populating Historical Data"
  echo "================================================"
  cd /app/src && python main.py
  cd /app
  echo "✓ Data population completed"
fi

# Start the API
echo ""
echo "================================================"
echo "   Starting FastAPI Server"
echo "================================================"
echo "API will be available at http://localhost:8000"
echo "Documentation at http://localhost:8000/docs"
echo "================================================"
echo ""

exec python /app/run_api.py

