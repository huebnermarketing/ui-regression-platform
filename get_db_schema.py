import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
config = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'ui_diff_dashboard'),
    'charset': 'utf8mb4'
}

try:
    # Connect to MySQL
    connection = pymysql.connect(**config)
    cursor = connection.cursor()
    
    print("Connected to MySQL database")
    print("=" * 50)
    
    # Get all tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print("Tables in the database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "=" * 50)
    
    # Get schema for each table
    for table in tables:
        table_name = table[0]
        print(f"\nSchema for table '{table_name}':")
        print("-" * 30)
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        for column in columns:
            field, type, null, key, default, extra = column
            print(f"  {field} {type} {null} {key} {default} {extra}")
    
except pymysql.Error as err:
    print(f"Error: {err}")
    
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'connection' in locals():
        connection.close()
        print("\nDatabase connection closed")