#!/bin/bash
# =============================================================================
# Pre-start script - Runs before the application starts
# Handles: database table creation, migrations, startup validation
# =============================================================================

# Do NOT use set -e here - individual steps should not crash the startup
# set -e

echo "=== DCLM Payroll - Pre-start Setup ==="

# 1. Check that critical environment variables are set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL is not set! Database operations will fail."
fi

if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY is not set!"
    exit 1
fi

# 2. Create required directories first (before DB attempt)
mkdir -p /app/payslips 2>/dev/null || true
chmod 777 /app/payslips 2>/dev/null || true
echo "Directory /app/payslips ready."

# 3. Auto-create database tables (uses SQLAlchemy metadata)
#    In production, use Alembic for proper migration management
echo "Creating/updating database tables..."
python -c "
from app.core.database import engine, Base
import app.models  # noqa: F401 - ensures all models are loaded
Base.metadata.create_all(bind=engine)
print('Database tables verified successfully.')
" || echo "WARNING: Database tables could not be created. App will still start."

# 4. Run schema migrations for new columns
echo "Running schema migrations..."
python << 'PYEOF'
from app.core.database import engine
import sqlalchemy as sa

migrations = [
    ("staff_category", "ALTER TABLE payroll_records ADD COLUMN staff_category VARCHAR(20) DEFAULT 'pastoral'"),
    ("rent_monthly", "ALTER TABLE payroll_records ADD COLUMN rent_monthly FLOAT DEFAULT 0"),
    ("utility_monthly", "ALTER TABLE payroll_records ADD COLUMN utility_monthly FLOAT DEFAULT 0"),
    ("transport_monthly", "ALTER TABLE payroll_records ADD COLUMN transport_monthly FLOAT DEFAULT 0"),
    ("pf_eight_percent", "ALTER TABLE payroll_records ADD COLUMN pf_eight_percent FLOAT DEFAULT 0"),
    ("ssnit_deduction", "ALTER TABLE payroll_records ADD COLUMN ssnit_deduction FLOAT DEFAULT 0"),
]

with engine.connect() as conn:
    result = conn.execute(sa.text('SHOW COLUMNS FROM payroll_records'))
    existing = [row[0] for row in result]

    for col_name, alter_sql in migrations:
        if col_name not in existing:
            try:
                conn.execute(sa.text(alter_sql))
                conn.commit()
                print(f'  + Added column: {col_name}')
            except Exception as e:
                conn.rollback()
                print(f'  - Could not add {col_name}: {e}')
        else:
            print(f'  ✓ Column exists: {col_name}')

print("Running upload_history migrations...")
upload_migrations = [
    ("total_employees", "ALTER TABLE upload_history ADD COLUMN total_employees INTEGER DEFAULT 0"),
    ("imported_count", "ALTER TABLE upload_history ADD COLUMN imported_count INTEGER DEFAULT 0"),
    ("skipped_count", "ALTER TABLE upload_history ADD COLUMN skipped_count INTEGER DEFAULT 0"),
    ("skip_reasons", "ALTER TABLE upload_history ADD COLUMN skip_reasons TEXT"),
    ("payroll_type", "ALTER TABLE upload_history ADD COLUMN payroll_type VARCHAR(50)"),
    ("unmatched_count", "ALTER TABLE upload_history ADD COLUMN unmatched_count INTEGER DEFAULT 0"),
]

print("Creating upload_mismatches table...")
try:
    from app.models.upload_mismatch import UploadMismatch
    Base.metadata.create_all(bind=engine)
    print('  ✓ upload_mismatches table ready')
except Exception as e:
    print(f'  - Could not create upload_mismatches: {e}')

try:
    result = conn.execute(sa.text('SHOW COLUMNS FROM upload_history'))
    upload_existing = [row[0] for row in result]

    for col_name, alter_sql in upload_migrations:
        if col_name not in upload_existing:
            try:
                conn.execute(sa.text(alter_sql))
                conn.commit()
                print(f'  + Added column: {col_name} to upload_history')
            except Exception as e:
                conn.rollback()
                print(f'  - Could not add {col_name}: {e}')
        else:
            print(f'  ✓ Column exists: {col_name} in upload_history')
except Exception as e:
    print(f'  - Could not inspect upload_history: {e}')
PYEOF
PYEXIT=$?
if [ $PYEXIT -ne 0 ]; then
    echo "WARNING: Migration script exited with code $PYEXIT. Some columns may not have been added."
fi

echo "=== Pre-start complete. Starting application... ==="

# 4. Start the application with uvicorn
# Using exec to replace the shell process so signals are handled correctly
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${APP_PORT:-8000} \
    --workers ${APP_WORKERS:-4} \
    --proxy-headers \
    --forwarded-allow-ips '*'

