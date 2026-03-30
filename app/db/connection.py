import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def get_conn():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            sslmode="require",
            options="-c timezone=America/Mexico_City"            
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None