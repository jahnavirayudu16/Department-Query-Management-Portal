import sqlite3
from flask import g, current_app
from config import Config
from models import check_and_migrate_db, init_db

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")          # Concurrent reads + writes
        g.db.execute("PRAGMA synchronous = NORMAL")        # High performance with crash safety
        g.db.execute("PRAGMA cache_size = -16000")         # 16 MB in-memory cache
        g.db.execute("PRAGMA temp_store = MEMORY")         # Temp tables and sorting in RAM
        g.db.execute("PRAGMA mmap_size = 268435456")       # 256 MB memory-mapped I/O
        g.db.execute("PRAGMA busy_timeout = 5000")         # Wait up to 5s instead of throwing locked error
    return g.db

def get_standalone_db():
    """Provides a standalone database connection outside Flask application context (e.g. seed scripts, tests)."""
    db = sqlite3.connect(Config.DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
