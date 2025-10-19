import sqlite3
import os

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect('account_unlock.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Creates the necessary tables in the database if they don't exist."""
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, email TEXT NOT NULL, phone_number TEXT, status TEXT NOT NULL CHECK(status IN ('active', 'locked')))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS otps (user_id TEXT PRIMARY KEY, otp TEXT NOT NULL, expiry_time DATETIME NOT NULL, FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS escalation_tickets (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, issue_description TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    conn.commit()
    conn.close()

def seed_data():
    """Seeds the database with initial sample data, but only if it's empty."""
    conn = get_db_connection()
    # Check if the user already exists to prevent re-seeding on server restarts
    user_exists = conn.execute("SELECT 1 FROM users WHERE user_id = ?", ('john.doe',)).fetchone()
    if not user_exists:
        conn.execute("INSERT INTO users (user_id, email, phone_number, status) VALUES (?, ?, ?, ?)",('john.doe', '22pa1a0514@vishnu.edu.in', '+917680804985', 'locked'))
        conn.execute("INSERT INTO users (user_id, email, phone_number, status) VALUES (?, ?, ?, ?)",('jane.doe', 'jane.doe@example.com', '+15557654321', 'active'))
        print("Database seeded with initial data.")
        conn.commit()
    else:
        print("Data already exists, skipping seed.")
    conn.close()

def initialize_database():
    """A helper function to run the entire database setup process."""
    print("Initializing database...")
    create_tables()
    seed_data()
    print("Database initialization complete.")

if __name__ == '__main__':
    initialize_database()

