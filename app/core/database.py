from sqlalchemy import create_engine, pool, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Enhanced engine configuration for remote database
engine = create_engine(
    settings.database_url,
    poolclass=pool.QueuePool,
    pool_size=10,                          # Number of connections to keep in the pool
    max_overflow=20,                       # Maximum overflow connections
    pool_recycle=3600,                     # Recycle connections after 1 hour
    pool_pre_ping=True,                    # Test connections before using
    connect_args={
        'connect_timeout': 30,             # Connection timeout in seconds
        'read_timeout': 60,                # Read timeout for queries
        'write_timeout': 60,               # Write timeout for queries
        'charset': 'utf8mb4'
    },
    echo=False
)

# Set up connection event listeners
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set MySQL session variables for better compatibility"""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("SET SESSION max_allowed_packet=67108864")  # 64MB max packet
        cursor.execute("SET SESSION wait_timeout=600")              # 10 minute wait timeout
        cursor.execute("SET SESSION net_write_timeout=600")
        cursor.execute("SET SESSION net_read_timeout=600")
        cursor.close()
    except Exception as e:
        print(f"Warning: Could not set MySQL session variables: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and performance indexes."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified.")
    except Exception as e:
        logger.warning(f"Could not create tables (non-critical): {e}")
    
    try:
        conn = engine.connect()
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_payroll_month ON payroll_records(month);
            CREATE INDEX IF NOT EXISTS idx_payroll_employee_name ON payroll_records(employee_name);
            CREATE INDEX IF NOT EXISTS idx_payroll_month_employee ON payroll_records(month, employee_name);
            CREATE INDEX IF NOT EXISTS idx_employee_name ON employees(name);
            CREATE INDEX IF NOT EXISTS idx_employee_email ON employees(email);
            CREATE INDEX IF NOT EXISTS idx_employee_number ON employees(employee_number);
            CREATE INDEX IF NOT EXISTS idx_upload_created_at ON upload_history(created_at);
            CREATE INDEX IF NOT EXISTS idx_upload_month ON upload_history(month);
        """))
        conn.commit()
        conn.close()
        logger.info("Performance indexes created/verified.")
    except Exception as e:
        logger.warning(f"Could not create indexes (non-critical): {e}")

# Import text for raw SQL
from sqlalchemy import text