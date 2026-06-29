from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# --- Engine ---
# pool_pre_ping=True: checks connection health before using it from the pool.
# Prevents "connection already closed" errors after PostgreSQL restarts.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,          # number of persistent connections in the pool
    max_overflow=10,      # extra connections allowed beyond pool_size under load
)

# --- Session factory ---
# autocommit=False : you must call db.commit() explicitly — prevents accidental writes
# autoflush=False  : SQLAlchemy won't flush pending changes automatically before queries
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)