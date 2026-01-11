#!/bin/bash
set -e

# DeepAgentStudio Backend Entrypoint
# This script ensures migrations are applied before the application starts

echo "=== DeepAgentStudio Backend Startup ==="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
import sys
from sqlalchemy import create_engine, text
import os

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print('DATABASE_URL not set')
    sys.exit(1)

try:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('PostgreSQL is ready')
    sys.exit(0)
except Exception as e:
    print(f'Waiting... ({e})')
    sys.exit(1)
" 2>&1; then
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Attempt $RETRY_COUNT/$MAX_RETRIES - PostgreSQL not ready, waiting..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: PostgreSQL did not become ready in time"
    exit 1
fi

# Run database migrations
echo "Running database migrations..."
cd /app
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "Migrations completed successfully"
else
    echo "ERROR: Migration failed"
    exit 1
fi

# Start the application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
