"""
Migration script to add 'capture_and_diff_complete' to project_pages status ENUM
Run this script to add the missing status value
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_capture_and_diff_complete_status():
    """Add 'capture_and_diff_complete' to project_pages status ENUM"""
    
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
        
        # Check current ENUM values
        cursor.execute("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'project_pages' 
            AND COLUMN_NAME = 'status'
        """, (config['database'],))
        
        result = cursor.fetchone()
        if result:
            current_enum = result[0]
            print(f"Current status ENUM: {current_enum}")
            
            # Check if 'capture_and_diff_complete' is already in the ENUM
            if 'capture_and_diff_complete' in current_enum:
                print("WARNING: 'capture_and_diff_complete' already exists in status ENUM. Skipping migration.")
                return True
        
        # Add 'capture_and_diff_complete' to the ENUM
        alter_table_query = """
        ALTER TABLE project_pages 
        MODIFY COLUMN status ENUM(
            'pending', 
            'crawled', 
            'ready_for_screenshot', 
            'screenshot_complete', 
            'screenshot_failed', 
            'ready_for_diff', 
            'diff_pending', 
            'diff_running', 
            'diff_generated', 
            'diff_failed',
            'capture_and_diff_complete'
        ) NOT NULL DEFAULT 'pending'
        """
        
        cursor.execute(alter_table_query)
        print("[SUCCESS] Added 'capture_and_diff_complete' to project_pages status ENUM")
        
        # Commit the changes
        connection.commit()
        print("[SUCCESS] Migration completed successfully!")
        
    except pymysql.Error as err:
        print(f"Error: {err}")
        if connection:
            connection.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("Database connection closed")
    
    return True

def check_enum_value_exists():
    """Check if 'capture_and_diff_complete' already exists in status ENUM"""
    config = {
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'ui_diff_dashboard'),
        'charset': 'utf8mb4'
    }
    
    try:
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'project_pages' 
            AND COLUMN_NAME = 'status'
        """, (config['database'],))
        
        result = cursor.fetchone()
        if result:
            return 'capture_and_diff_complete' in result[0]
        return False
        
    except pymysql.Error as err:
        print(f"Error checking ENUM value existence: {err}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == '__main__':
    print("Adding 'capture_and_diff_complete' to project_pages status ENUM...")
    print("=" * 60)
    
    # Check if ENUM value already exists
    if check_enum_value_exists():
        print("WARNING: 'capture_and_diff_complete' already exists in status ENUM. Skipping migration.")
    else:
        # Add the ENUM value
        if add_capture_and_diff_complete_status():
            print("\nSUCCESS: Migration completed successfully!")
            print("The 'capture_and_diff_complete' status has been added to project_pages table.")
        else:
            print("\nERROR: Migration failed!")
            print("Please check the error messages above and try again.")