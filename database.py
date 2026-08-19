import sqlite3
from flask import g, current_app

def get_db():
    """Get or create SQLite database connection for current request context."""
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE_PATH', 'insurance_app.db')
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        # Enable Foreign Key support in SQLite
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Initialize database tables using parameterized schema definitions."""
    if app:
        with app.app_context():
            db = get_db()
            _create_tables(db)
    else:
        db = get_db()
        _create_tables(db)

def _create_tables(db):
    """Execute DDL statements to set up tables if they do not exist."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            age REAL NOT NULL,
            sex TEXT NOT NULL,
            bmi REAL NOT NULL,
            children INTEGER NOT NULL,
            smoker TEXT NOT NULL,
            region TEXT NOT NULL,
            predicted_cost REAL NOT NULL,
            created_at DATETIME DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_predictions_user_id ON predictions(user_id);
        CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);
    """)
    db.commit()
