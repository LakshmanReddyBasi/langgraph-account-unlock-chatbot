import sqlite3
import os

DB_PATH = "account_unlock.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            phone_number TEXT,
            status TEXT NOT NULL CHECK(status IN ('active', 'locked'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS otps (
            user_id TEXT PRIMARY KEY,
            otp TEXT NOT NULL,
            expiry_time DATETIME NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS escalation_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            issue_description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def seed_data():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users")
    c.execute("DELETE FROM otps")
    c.execute("DELETE FROM escalation_tickets")
    try:
        c.execute(
            "INSERT INTO users (user_id, email, phone_number, status) VALUES (?, ?, ?, ?)",
            ('john.doe', '22pa1a0514@vishnu.edu.in', '+917680804985', 'locked')
        )
    except sqlite3.IntegrityError:
        pass
    try:
        c.execute(
            "INSERT INTO users (user_id, email, phone_number, status) VALUES (?, ?, ?, ?)",
            ('jane.doe', 'jane@example.com', '+15551234567', 'active')
        )
    except sqlite3.IntegrityError:
        pass
    conn.commit()
    conn.close()