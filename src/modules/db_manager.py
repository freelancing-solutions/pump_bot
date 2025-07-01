import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from src.config import Config


class DBManager:
    def __init__(self, settings: Config):
        self.db_path = settings.DB_PATH

    
    def init_db(self):
        """Initialize database connection and create tables if needed."""
        with self.get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute(self, query: str, params: Optional[Tuple] = None) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        with self.get_connection() as conn:
            return conn.execute(query, params or ())
    
    def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict]:
        """Fetch single row as dictionary."""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        """Fetch all rows as list of dictionaries."""
        cursor = self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert data and return last row ID."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], where: str, params: Tuple = ()) -> int:
        """Update records and return affected row count."""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        cursor = self.execute(query, tuple(data.values()) + params)
        return cursor.rowcount
    
    def delete(self, table: str, where: str, params: Tuple = ()) -> int:
        """Delete records and return affected row count."""
        query = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(query, params)
        return cursor.rowcount
    
    def create_table(self, table: str, schema: str):
        """Create table with given schema."""
        query = f"CREATE TABLE IF NOT EXISTS {table} ({schema})"
        self.execute(query)
    
    def table_exists(self, table: str) -> bool:
        """Check if table exists."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        return self.fetch_one(query, (table,)) is not None
