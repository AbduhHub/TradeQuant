"""
Database Connection Manager
============================
Handles SQLite database connections and session management.

Author: Trading Engine v2.0
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from .models import Base


class DatabaseManager:
    """
    Manages database connections and sessions.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. 
                    If None, uses default 'trading_engine.db' in project root.
        """
        if db_path is None:
            # Default: database in project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, 'trading_engine.db')
        
        self.db_path = db_path
        self.engine = None
        self.session_factory = None
        self.Session = None
        
    def initialize(self, echo: bool = False):
        """
        Initialize database connection and create tables.
        
        Args:
            echo: If True, SQLAlchemy will log all SQL statements
        """
        # Create engine
        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            echo=echo,
            connect_args={'check_same_thread': False}  # For SQLite
        )
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        print(f"✅ Database initialized: {self.db_path}")
        
    def get_session(self):
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy session
        """
        if self.Session is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.Session()
    
    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope for database operations.
        
        Usage:
            with db_manager.session_scope() as session:
                session.add(backtest)
                session.commit()
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def close(self):
        """
        Close database connection.
        """
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
        
        print("✅ Database connection closed")
    
    def reset_database(self):
        """
        Drop all tables and recreate them.
        WARNING: This will delete all data!
        """
        if self.engine is None:
            raise RuntimeError("Database not initialized.")
        
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        
        print("⚠️  Database reset complete. All data deleted.")


# Global database manager instance
_db_manager = None


def get_db_manager(db_path: str = None) -> DatabaseManager:
    """
    Get the global database manager instance (singleton pattern).
    
    Args:
        db_path: Path to database file (only used on first call)
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
        _db_manager.initialize()
    
    return _db_manager


def reset_db_manager():
    """
    Reset the global database manager (useful for testing).
    """
    global _db_manager
    if _db_manager:
        _db_manager.close()
    _db_manager = None
