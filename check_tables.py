import sqlite3
import os

db_path = 'test.db'
if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables in database:")
    for table in tables:
        table_name = table[0]
        print(f"  - {table_name}")
        
        # Get row count for each table
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    Records: {count}")
        except Exception as e:
            print(f"    Error counting records: {e}")
    
    print("\nChecking specific tables:")
    # Check if diff_jobs and screenshot_jobs exist
    for table_name in ['diff_jobs', 'screenshot_jobs']:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"{table_name}: {count} records")
            
            # Get schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"  Columns: {[col[1] for col in columns]}")
            
        except sqlite3.OperationalError as e:
            print(f"{table_name}: Table does not exist")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")