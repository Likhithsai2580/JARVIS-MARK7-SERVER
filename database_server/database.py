from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
from typing import Generator
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

@contextmanager
def get_db() -> Generator:
    """Get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Initialize database with all tables."""
    from .models import User, Session, Command, UserSettings  # Import models
    Base.metadata.create_all(bind=engine)

def get_db_session():
    """Dependency for FastAPI to get database session."""
    with get_db() as session:
        yield session

class DatabaseError(Exception):
    """Base class for database errors."""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass

class DatabaseQueryError(DatabaseError):
    """Raised when database query fails."""
    pass

async def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        with get_db() as session:
            session.execute("SELECT 1")
        return True
    except Exception as e:
        raise DatabaseConnectionError(f"Database connection failed: {str(e)}")

def cleanup_expired_sessions() -> None:
    """Cleanup expired sessions from database."""
    from datetime import datetime
    from .models import Session
    
    try:
        with get_db() as session:
            expired = session.query(Session).filter(
                Session.expires_at < datetime.utcnow()
            ).all()
            
            for exp_session in expired:
                exp_session.is_active = False
            
            session.commit()
    except Exception as e:
        raise DatabaseQueryError(f"Failed to cleanup expired sessions: {str(e)}")

def get_database_stats() -> dict:
    """Get database statistics."""
    from .models import User, Session, Command, UserSettings
    
    try:
        with get_db() as session:
            return {
                "users": session.query(User).count(),
                "active_sessions": session.query(Session).filter(Session.is_active == True).count(),
                "total_commands": session.query(Command).count(),
                "active_users": session.query(User).filter(User.is_active == True).count()
            }
    except Exception as e:
        raise DatabaseQueryError(f"Failed to get database stats: {str(e)}")

def vacuum_database() -> None:
    """Optimize database by running VACUUM (SQLite) or ANALYZE (PostgreSQL)."""
    try:
        if DATABASE_URL.startswith('sqlite'):
            with engine.connect() as conn:
                conn.execute('VACUUM')
        else:
            with engine.connect() as conn:
                conn.execute('ANALYZE')
    except Exception as e:
        raise DatabaseError(f"Failed to optimize database: {str(e)}")

def backup_database(backup_path: str) -> None:
    """Create database backup."""
    try:
        if DATABASE_URL.startswith('sqlite'):
            import shutil
            db_path = DATABASE_URL.replace('sqlite:///', '')
            shutil.copy2(db_path, backup_path)
        else:
            # For PostgreSQL, use pg_dump
            import subprocess
            subprocess.run(['pg_dump', '-f', backup_path, DATABASE_URL], check=True)
    except Exception as e:
        raise DatabaseError(f"Failed to backup database: {str(e)}")

def restore_database(backup_path: str) -> None:
    """Restore database from backup."""
    try:
        if DATABASE_URL.startswith('sqlite'):
            import shutil
            db_path = DATABASE_URL.replace('sqlite:///', '')
            shutil.copy2(backup_path, db_path)
        else:
            # For PostgreSQL, use psql
            import subprocess
            subprocess.run(['psql', DATABASE_URL, '-f', backup_path], check=True)
    except Exception as e:
        raise DatabaseError(f"Failed to restore database: {str(e)}") 