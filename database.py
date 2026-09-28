import os
import re
import sqlite3
from flask import g, current_app
from config import Config
from models import check_and_migrate_db, init_db

DATABASE_URL = os.environ.get('DATABASE_URL')
IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://')))

def get_db():
    """Opens a database connection (SQLite or PostgreSQL) for the current application context.
    Cached on Flask's g object so at most one connection is acquired per request."""
    if 'db' not in g:
        if IS_POSTGRES:
            try:
                import psycopg2
                import psycopg2.extras
                pg_url = DATABASE_URL
                if pg_url.startswith("postgres://"):
                    pg_url = pg_url.replace("postgres://", "postgresql://", 1)
                conn = psycopg2.connect(pg_url, cursor_factory=psycopg2.extras.RealDictCursor)
                g.db = conn
                g.db_type = 'postgres'
                return g.db
            except Exception as e:
                # Graceful fallback to SQLite if PostgreSQL driver is unavailable
                pass

        # Default high-performance SQLite engine with WAL mode and memory buffers
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=30.0,
            autocommit=True
        )
        g.db.row_factory = sqlite3.Row
        g.db_type = 'sqlite'
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")          # Concurrent reads + writes
        g.db.execute("PRAGMA synchronous = NORMAL")        # High performance with crash safety
        g.db.execute("PRAGMA cache_size = -16000")         # 16 MB in-memory cache
        g.db.execute("PRAGMA temp_store = MEMORY")         # Temp tables and sorting in RAM
        g.db.execute("PRAGMA mmap_size = 268435456")       # 256 MB memory-mapped I/O
        g.db.execute("PRAGMA busy_timeout = 30000")        # Wait up to 30s under concurrent write spikes
    return g.db

def get_standalone_db():
    """Provides a standalone database connection outside Flask application context (e.g. seed scripts, tests)."""
    if IS_POSTGRES:
        try:
            import psycopg2
            import psycopg2.extras
            pg_url = DATABASE_URL
            if pg_url.startswith("postgres://"):
                pg_url = pg_url.replace("postgres://", "postgresql://", 1)
            return psycopg2.connect(pg_url, cursor_factory=psycopg2.extras.RealDictCursor)
        except Exception:
            pass

    db = sqlite3.connect(Config.DATABASE, timeout=30.0, autocommit=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA synchronous = NORMAL")
    db.execute("PRAGMA busy_timeout = 30000")
    return db

def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
