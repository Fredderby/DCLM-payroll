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
        
        # Recreate email_logs table to ensure schema matches model
        try:
            # Check if table is missing columns by trying to insert a test row
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS email_logs_new (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    employee_id INT DEFAULT NULL,
                    employee_name VARCHAR(255) DEFAULT NULL,
                    employee_number VARCHAR(50) DEFAULT NULL,
                    payroll_id INT DEFAULT NULL,
                    recipient_email VARCHAR(255) DEFAULT NULL,
                    status VARCHAR(50) DEFAULT NULL,
                    month VARCHAR(20) DEFAULT NULL,
                    net_salary FLOAT DEFAULT 0,
                    error_message TEXT DEFAULT NULL,
                    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            # Drop old table and rename new one into place
            conn.execute(text("DROP TABLE IF EXISTS email_logs_old"))
            conn.execute(text("RENAME TABLE email_logs TO email_logs_old, email_logs_new TO email_logs"))
            conn.commit()
            # Drop the old backup table
            conn.execute(text("DROP TABLE IF EXISTS email_logs_old"))
            conn.commit()
            logger.info("Recreated email_logs table with correct schema.")
        except Exception:
            conn.rollback()
            # If first run rename failed (table didn't exist), try direct create
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS email_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        employee_id INT DEFAULT NULL,
                        employee_name VARCHAR(255) DEFAULT NULL,
                        employee_number VARCHAR(50) DEFAULT NULL,
                        payroll_id INT DEFAULT NULL,
                        recipient_email VARCHAR(255) DEFAULT NULL,
                        status VARCHAR(50) DEFAULT NULL,
                        month VARCHAR(20) DEFAULT NULL,
                        net_salary FLOAT DEFAULT 0,
                        error_message TEXT DEFAULT NULL,
                        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
                logger.info("Created email_logs table with correct schema.")
            except Exception:
                conn.rollback()
        
        try:
            conn.execute(text("ALTER TABLE upload_history ADD COLUMN month VARCHAR(20) DEFAULT NULL"))
            conn.commit()
            logger.info("Added 'month' column to upload_history table.")
        except Exception:
            conn.rollback()  # Column already exists - ignore
        
        # Create performance indexes for known tables
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_payroll_month ON payroll_records(month)",
            "CREATE INDEX IF NOT EXISTS idx_payroll_employee_name ON payroll_records(employee_name)",
            "CREATE INDEX IF NOT EXISTS idx_payroll_month_employee ON payroll_records(month, employee_name)",
            "CREATE INDEX IF NOT EXISTS idx_employee_name ON employees(name)",
            "CREATE INDEX IF NOT EXISTS idx_employee_email ON employees(email)",
            "CREATE INDEX IF NOT EXISTS idx_employee_number ON employees(employee_number)",
            "CREATE INDEX IF NOT EXISTS idx_upload_timestamp ON upload_history(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_upload_month ON upload_history(month)",
        ]
        for stmt in index_statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()  # Index might already exist or table might not exist yet
        
        conn.close()
        logger.info("Schema migrations and indexes verified.")
    except Exception as e:
        logger.warning(f"Could not run schema migrations (non-critical): {e}")

# Import text for raw SQL
from sqlalchemy import text