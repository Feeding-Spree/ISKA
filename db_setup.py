import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

def initialize_database():
    # Connect to the database file
    conn = sqlite3.connect('iska_database.db')
    cursor = conn.cursor()

    # 1. Announcements Table: Campus news and alerts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_en TEXT NOT NULL,
            title_tl TEXT NOT NULL,
            content_en TEXT NOT NULL,
            content_tl TEXT NOT NULL,
            posted_by TEXT,
            is_active INTEGER DEFAULT 1,
            date_posted TEXT
        )
    ''')

    # 2. Kiosk Info Table: Trigger keywords and FAQs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kiosk_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            response_en TEXT NOT NULL,
            response_tl TEXT NOT NULL,
            category TEXT,
            posted_by TEXT,
            last_updated TEXT
        )
    ''')

    # 3. Query Logs Table: Analytics and session transcripts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_query TEXT,
            timestamp TEXT,
            ai_response TEXT,
            session_id TEXT
        )
    ''')

    # 4. Users Table: Secure administrator credentials
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    # Initial Setup: Create the master administrator account if it doesn't exist
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        # Using the project master password: PUP1904
        hashed_password = generate_password_hash('PUP1904')
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ('admin', hashed_password)
        )
        print("[+] Master admin account created successfully.")

    conn.commit()
    conn.close()
    print("[+] ISKA Database initialized with all 4 core tables.")

if __name__ == "__main__":
    initialize_database()