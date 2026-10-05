# database_init.py created by DOV1NTC powered by XWARED TEAM(C)
import sqlite3
import os
from utils.log import log
from utils.load_env import get_path_to_db

def get_db(base_dir: str):
    db_filename = get_path_to_db()
    
    if not db_filename:
        log("DB_PATH is not set in .env", "error")
        return None

    full_path = os.path.join(base_dir, db_filename)
    db_dir = os.path.dirname(full_path)
    if db_dir and not os.path.exists(db_dir):
        log(f"Database directory does not exist: {db_dir}", "error")
        return None

    try:
        conn = sqlite3.connect(full_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        log(f"Failed to connect to database: {e}", "error")
        return None

def init_db(base_dir: str):
    conn = get_db(base_dir)
    
    if conn is None:
        log("Database initialization FAILED: connection is None", "error")
        return False
        
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                mail TEXT UNIQUE NOT NULL,
                permissions TEXT DEFAULT 'user'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ip TEXT,
                device TEXT,
                browser TEXT,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invite_code INTEGER UNIQUE NOT NULL,
                owner_id TEXT NOT NULL,
                participants_session TEXT,
                session_data TEXT,
                stage INTEGER DEFAULT 1,
                question_id INTEGER DEFAULT 1,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connect_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                path TEXT NOT NULL,
                request_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        log("Database tables initialized successfully", "info")
        return True
        
    except Exception as e:
        log(f"Database initialization error: {e}", "error")
        return False
    finally:
        conn.close()