import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database using the DATABASE_URL.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    conn = psycopg2.connect(database_url)
    return conn

def create_tables():
    """Creates the necessary tables in the PostgreSQL database."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        # PostgreSQL uses SERIAL for auto-incrementing integers
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                phone_number TEXT,
                status TEXT NOT NULL CHECK(status IN ('active', 'locked'))
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS otps (
                user_id TEXT PRIMARY KEY,
                otp TEXT NOT NULL,
                expiry_time TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS escalation_tickets (
                ticket_id SERIAL PRIMARY KEY,
                user_id TEXT,
                issue_description TEXT,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
    conn.commit()
    conn.close()

def seed_data():
    """Seeds the database with initial sample data if it's empty."""
    conn = get_db_connection()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT 1 FROM users WHERE user_id = %s", ('john.doe',))
        user_exists = cur.fetchone()
        
        if not user_exists:
            # PostgreSQL uses %s for placeholders
            cur.execute(
                "INSERT INTO users (user_id, email, phone_number, status) VALUES (%s, %s, %s, %s)",
                ('john.doe', '22pa1a0514@vishnu.edu.in', '+917680804985', 'locked')
            )
            cur.execute(
                "INSERT INTO users (user_id, email, phone_number, status) VALUES (%s, %s, %s, %s)",
                ('jane.doe', 'jane.doe@example.com', '+15557654321', 'active')
            )
            print("Database seeded with initial data.")
        else:
            print("Data already exists, skipping seed.")
    conn.commit()
    conn.close()

def initialize_database():
    """A helper function to run the entire database setup process."""
    print("Initializing PostgreSQL database...")
    create_tables()
    seed_data()
    print("Database initialization complete.")

if __name__ == '__main__':
    initialize_database()

