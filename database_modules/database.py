import os
import psycopg2
from dotenv import load_dotenv

# Load .env from the root directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

# Supabase/PostgreSQL connection parameters
DB_HOST = os.environ.get("SUPABASE_DB_HOST", "your-supabase-host.supabase.co")
DB_PORT = os.environ.get("SUPABASE_DB_PORT", "5432")
DB_NAME = os.environ.get("SUPABASE_DB_NAME", "postgres")
DB_USER = os.environ.get("SUPABASE_DB_USER", "your-db-user")
DB_PASSWORD = os.environ.get("SUPABASE_DB_PASSWORD", "your-db-password")

def get_db_connection():
    """Establish a connection to the Supabase PostgreSQL database."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
        sslmode='require'
    )
    return conn

def create_table(conn):
    """Create the listings table if it doesn't exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            listing_id TEXT PRIMARY KEY,
            city TEXT NOT NULL,
            zipcode TEXT NOT NULL,
            listing_url TEXT NOT NULL,
            room_type TEXT,
            bedroom_count INTEGER,
            bathroom_count INTEGER
        );
    """)
    conn.commit()
    cur.close()

def insert_listing(conn, listing_data):
    """
    Insert a listing into the database.
    listing_data should be a dictionary containing:
    - listing_id, city, zipcode, listing_url, room_type, bedroom_count, bathroom_count
    Uses PostgreSQL's ON CONFLICT DO NOTHING to avoid duplicate entries.
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO listings (listing_id, city, zipcode, listing_url, room_type, bedroom_count, bathroom_count)
            VALUES (%(listing_id)s, %(city)s, %(zipcode)s, %(listing_url)s, %(room_type)s, %(bedroom_count)s, %(bathroom_count)s)
            ON CONFLICT (listing_id) DO NOTHING;
        """, listing_data)
        conn.commit()
    except Exception as e:
        print(f"Error inserting {listing_data.get('listing_url')}: {e}")
        conn.rollback()
    cur.close()
