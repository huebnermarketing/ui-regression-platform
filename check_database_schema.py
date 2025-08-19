import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASSWORD', '')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')

try:
    # Connect to MySQL database
    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        charset='utf8mb4'
    )
    
    with connection.cursor() as cursor:
        # Check if the projects table exists and show its structure
        cursor.execute("DESCRIBE projects")
        columns = cursor.fetchall()
        
        print("Current projects table structure:")
        print("-" * 50)
        for column in columns:
            print(f"{column[0]:<25} {column[1]:<15} {column[2]:<5} {column[3]:<5} {column[4] or '':<10} {column[5] or ''}")
        
        print("\n" + "-" * 50)
        
        # Check if is_page_restricted column exists
        has_column = any(col[0] == 'is_page_restricted' for col in columns)
        print(f"is_page_restricted column exists: {has_column}")
        
        if not has_column:
            print("\nAdding is_page_restricted column...")
            cursor.execute("""
                ALTER TABLE projects 
                ADD COLUMN is_page_restricted BOOLEAN NOT NULL DEFAULT FALSE
            """)
            connection.commit()
            print("Column added successfully!")
        else:
            print("Column already exists in database.")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'connection' in locals():
        connection.close()