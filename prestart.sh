#!/bin/bash
# =============================================================================
# Pre-start script - Runs before the application starts
# Handles: database table creation, migrations, startup validation
# =============================================================================

set -e

echo "=== DCLM Payroll - Pre-start Setup ==="

# 1. Check that critical environment variables are set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set!"
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY is not set!"
    exit 1
fi

# 2. Auto-create database tables (uses SQLAlchemy metadata)
#    In production, use Alembic for proper migration management
echo "Creating/updating database tables..."
python -c "
from app.core.database import engine, Base
import app.models  # noqa: F401 - ensures all models are loaded
Base.metadata.create_all(bind=engine)
print('Database tables verified successfully.')
"

# 3. Create required directories
mkdir -p /app/payslips
chmod 777 /app/payslips
echo "Directory /app/payslips ready."

echo "=== Pre-start complete. Starting application... ==="

# 4. Start the application with uvicorn
# Using exec to replace the shell process so signals are handled correctly
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${APP_PORT:-8000} \
    --workers ${APP_WORKERS:-4} \
    --proxy-headers \
    --forwarded-allow-ips '*'

