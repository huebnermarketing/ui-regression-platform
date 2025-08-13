"""
Rollback script to remove 'capture_and_diff_complete' from project_pages status ENUM
This undoes the changes made by add_capture_and_diff_complete_status.py
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def rollback_capture_and_diff_complete_status():
    """Remove 'capture_and_diff_complete' from project_pages status ENUM"""
    
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
            
            # Check if 'capture_and_diff_complete' exists in the ENUM
            if 'capture_and_diff_complete' not in current_enum:
                print("WARNING: 'capture_and_diff_complete' not found in status ENUM. Nothing to rollback.")
                return True
        
        # First, update any records using 'capture_and_diff_complete' to a valid status
        cursor.execute("""
            UPDATE project_pages 
            SET status = 'diff_generated' 
            WHERE status = 'capture_and_diff_complete'
        """)
        
        updated_rows = cursor.rowcount
        if updated_rows > 0:
            print(f"Updated {updated_rows} records from 'capture_and_diff_complete' to 'diff_generated'")
        
        # Remove 'capture_and_diff_complete' from the ENUM
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
            'diff_failed'
        ) NOT NULL DEFAULT 'pending'
        """
        
        cursor.execute(alter_table_query)
        print("[SUCCESS] Removed 'capture_and_diff_complete' from project_pages status ENUM")
        
        # Commit the changes
        connection.commit()
        print("[SUCCESS] Rollback completed successfully!")
        
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

if __name__ == '__main__':
    print("Rolling back 'capture_and_diff_complete' status from project_pages ENUM...")
    print("=" * 70)
    
    if rollback_capture_and_diff_complete_status():
        print("\nSUCCESS: Rollback completed successfully!")
        print("The 'capture_and_diff_complete' status has been removed from project_pages table.")
    else:
        print("\nERROR: Rollback failed!")
        print("Please check the error messages above and try again.")