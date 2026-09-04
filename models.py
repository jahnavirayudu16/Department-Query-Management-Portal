import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    icon TEXT DEFAULT 'building',
    head_name TEXT,
    contact_email TEXT,
    avg_response_minutes INTEGER DEFAULT 15,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT 'Anonymous User',
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    level TEXT,
    department TEXT,
    course TEXT,
    year INTEGER,
    phone TEXT,
    roll_no TEXT,
    designation TEXT,
    is_active INTEGER DEFAULT 1,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Academics',
    department TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Medium',
    status TEXT NOT NULL DEFAULT 'New',
    assigned_staff_id INTEGER,
    is_routed_manually INTEGER DEFAULT 0,
    admin_reviewed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_response_at TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(assigned_staff_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_internal_note INTEGER DEFAULT 0,
    attachment_filename TEXT,
    attachment_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(query_id) REFERENCES queries(id) ON DELETE CASCADE,
    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    query_id INTEGER,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(query_id) REFERENCES queries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL,
    message_id INTEGER,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    file_type TEXT,
    filepath TEXT NOT NULL,
    uploaded_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(query_id) REFERENCES queries(id) ON DELETE CASCADE,
    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE SET NULL,
    FOREIGN KEY(uploaded_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(query_id) REFERENCES queries(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(query_id) REFERENCES queries(id) ON DELETE SET NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS admin_hod_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    department TEXT,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_department ON queries(department);
CREATE INDEX IF NOT EXISTS idx_queries_category ON queries(category);
CREATE INDEX IF NOT EXISTS idx_queries_status ON queries(status);
CREATE INDEX IF NOT EXISTS idx_queries_priority ON queries(priority);
CREATE INDEX IF NOT EXISTS idx_messages_query_id ON messages(query_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_hod_sender ON admin_hod_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_admin_hod_receiver ON admin_hod_messages(receiver_id);
"""

def check_and_migrate_db(db_conn):
    """Automatically adds missing columns to existing database tables if schema was updated."""
    try:
        cursor = db_conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'level' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN level TEXT")
        if 'course' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN course TEXT")
        if 'year' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN year INTEGER")
        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        if 'last_active_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
        cursor.execute("PRAGMA table_info(admin_hod_messages)")
        msg_cols = [row[1] for row in cursor.fetchall()]
        if 'is_read' not in msg_cols:
            cursor.execute("ALTER TABLE admin_hod_messages ADD COLUMN is_read INTEGER DEFAULT 0")
            
        db_conn.commit()
    except Exception as e:
        print(f"Migration notice: {e}")

def init_db(db_conn):
    """Initializes the database schema."""
    db_conn.executescript(SCHEMA)
    check_and_migrate_db(db_conn)
    db_conn.commit()
