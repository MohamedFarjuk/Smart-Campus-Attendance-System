import os
import psycopg2
import pandas as pd

# Supabase Connection URL (Environment variable-la save panrathu safe)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:YOUR_PASSWORD@db.xxxx.supabase.co:5432/postgres")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_cloud_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Attendance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            name TEXT,
            roll_no TEXT,
            date TEXT,
            time TEXT,
            session TEXT,
            status TEXT
        )
    ''')
    
    # 2. Students Master Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT,
            parent_phone TEXT
        )
    ''')
    
    # 3. Notification Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_logs (
            id SERIAL PRIMARY KEY,
            name TEXT,
            roll_no TEXT,
            parent_phone TEXT,
            status TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

init_cloud_db()
