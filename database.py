# import os
# import psycopg2
# from psycopg2.extras import DictCursor
# from dotenv import load_dotenv
# from faker import Faker
# import random

# # Load environment variables from .env file
# load_dotenv()

# def get_db_connection():
#     """Establishes a connection to the PostgreSQL database."""
#     conn_string = os.getenv("DATABASE_URL")
#     if not conn_string:
#         raise ValueError("DATABASE_URL environment variable is not set.")
#     conn = psycopg2.connect(conn_string)
#     return conn

# def initialize_database():
#     """
#     Creates tables if they don't exist and seeds the database with sample data.
#     This function will now drop existing tables to ensure a fresh schema.
#     """
#     conn = get_db_connection()
#     with conn.cursor() as cur:
#         # Drop existing tables in reverse order of dependency to avoid foreign key errors
#         print("Dropping existing tables...")
#         cur.execute("DROP TABLE IF EXISTS escalation_tickets;")
#         cur.execute("DROP TABLE IF EXISTS otps;")
#         cur.execute("DROP TABLE IF EXISTS users;")
#         print("Tables dropped successfully.")

#         # Create users table with the 'full_name' column
#         print("Creating new tables...")
#         cur.execute('''
#             CREATE TABLE users (
#                 user_id TEXT PRIMARY KEY,
#                 full_name TEXT,
#                 email TEXT NOT NULL UNIQUE,
#                 phone_number TEXT,
#                 status TEXT NOT NULL CHECK(status IN ('active', 'locked'))
#             )
#         ''')
#         # Create otps table
#         cur.execute('''
#             CREATE TABLE otps (
#                 user_id TEXT PRIMARY KEY,
#                 otp TEXT NOT NULL,
#                 expiry_time TIMESTAMPTZ NOT NULL,
#                 FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
#             )
#         ''')
#         # Create escalation_tickets table
#         cur.execute('''
#             CREATE TABLE escalation_tickets (
#                 ticket_id SERIAL PRIMARY KEY,
#                 user_id TEXT,
#                 issue_description TEXT,
#                 timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
#             )
#         ''')
#         print("Tables created successfully.")

#         # Seeding data
#         print("Seeding database with initial data...")
#         seed_data(cur)
#         print("Seeding complete.")
        
#     conn.commit()
#     conn.close()

# def seed_data(cur):
#     """
#     Seeds the database with initial sample data, including 30+ fake users.
#     """
#     # NOTE FOR TESTING: To receive SMS OTPs, replace the placeholder phone number
#     # for 'john.doe' with your own phone number that you have verified with Twilio.
#     # The '+1555...' numbers are placeholders and will cause SMS to fail.
#     test_users = [
#         ('lakshman', 'Mr. Lakshman Reddy', '22pa1a0514@vishnu.edu.in', '+917680804985', 'locked'),
#         ('upendra', 'Mr. Upendra Chowdary', '22pa1a0542@vishnu.edu.in', '7659914797', 'locked'),
#         ('pavan', 'Mr. Pavan Kumar', '22pa1a0533@vishnu.edu.in', '7659914797', 'locked'),
#         ('john.doe', 'Mr. John Doe', 'john.doe@example.com', '+15550000001', 'locked'),

#     ]
    
#     for user in test_users:
#         cur.execute(
#             "INSERT INTO users (user_id, full_name, email, phone_number, status) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING",
#             user
#         )
        
#     # Generate 30 additional fake users
#     fake = Faker()
#     for _ in range(30):
#         full_name = fake.name()
#         first_name = full_name.split(' ')[0].lower()
#         last_name = full_name.split(' ')[-1].lower()
#         user_id = f"{first_name}.{last_name}"
        
#         email = f"{user_id}@{fake.domain_name()}"
#         phone_number = fake.phone_number()
#         status = random.choice(['locked', 'locked', 'active'])
        
#         cur.execute(
#             "INSERT INTO users (user_id, full_name, email, phone_number, status) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING",
#             (user_id, full_name, email, phone_number, status)
#         )

# if __name__ == '__main__':
#     print("Initializing and seeding the database manually...")
#     initialize_database()
#     print("Manual initialization complete.")


import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from faker import Faker
import random

load_dotenv()

def get_db_connection():
    conn_string = os.getenv("DATABASE_URL")
    if not conn_string:
        raise ValueError("DATABASE_URL environment variable is not set.")
    conn = psycopg2.connect(conn_string)
    return conn

def initialize_database():
    conn = get_db_connection()
    with conn.cursor() as cur:
        print("Dropping existing tables...")
        cur.execute("DROP TABLE IF EXISTS escalation_tickets;")
        cur.execute("DROP TABLE IF EXISTS otps;")
        cur.execute("DROP TABLE IF EXISTS users;")
        print("Tables dropped successfully.")

        print("Creating new tables...")
        cur.execute('''
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                full_name TEXT,
                email TEXT NOT NULL UNIQUE,
                phone_number TEXT,
                status TEXT NOT NULL CHECK(status IN ('active', 'locked')),
                last_otp_request TIMESTAMPTZ
            )
        ''')
        cur.execute('''
            CREATE TABLE otps (
                user_id TEXT PRIMARY KEY,
                otp_hash BYTEA NOT NULL,
                expiry_time TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        cur.execute('''
            CREATE TABLE escalation_tickets (
                ticket_id SERIAL PRIMARY KEY,
                user_id TEXT,
                issue_description TEXT,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("Tables created successfully.")

        print("Seeding database with initial data...")
        seed_data(cur)
        print("Seeding complete.")
        
    conn.commit()
    conn.close()

def seed_data(cur):
    test_users = [
        ('lakshman', 'Mr. Lakshman Reddy', '22pa1a0514@vishnu.edu.in', '+917680804985', 'locked'),
        ('upendra', 'Mr. Upendra Chowdary', '22pa1a0542@vishnu.edu.in', '+917659914797', 'locked'),
        ('pavan', 'Mr. Pavan Kumar', '22pa1a0533@vishnu.edu.in', '+917659914797', 'locked'),
        ('jane.doe', 'Ms. Jane Doe', 'jane.doe@example.com', '+15550000002', 'active'),
        ('alice.williams', 'Dr. Alice Williams', 'alice.w@example.com', '+15550000003', 'locked'),
        ('bob.jones', 'Mr. Bob Jones', 'bob.j@example.com', '+15550000004', 'locked'),
        ('charlie.brown', 'Mr. Charlie Brown', 'charlie.b@example.com', '+15550000005', 'locked')
    ]
    
    for user in test_users:
        cur.execute(
            "INSERT INTO users (user_id, full_name, email, phone_number, status, last_otp_request) VALUES (%s, %s, %s, %s, %s, NULL) ON CONFLICT (user_id) DO NOTHING",
            user
        )
        
    fake = Faker('en_IN')
    for _ in range(30):
        full_name = fake.name()
        first_name = full_name.split(' ')[0].lower()
        last_name = full_name.split(' ')[-1].lower()
        user_id = f"{first_name}.{last_name}"
        email = f"{user_id}@{fake.domain_name()}"
        phone_number = f"+91{fake.msisdn()[:10]}"
        status = random.choice(['locked', 'locked', 'active'])
        cur.execute(
            "INSERT INTO users (user_id, full_name, email, phone_number, status, last_otp_request) VALUES (%s, %s, %s, %s, %s, NULL) ON CONFLICT (user_id) DO NOTHING",
            (user_id, full_name, email, phone_number, status)
        )

if __name__ == '__main__':
    print("Initializing and seeding the database manually...")
    initialize_database()
    print("Manual initialization complete.")