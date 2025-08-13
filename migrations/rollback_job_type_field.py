"""
Rollback script to remove job_type field from crawl_jobs table
This undoes the changes made by add_job_type_field.py and add_job_type_field_mysql.py
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def rollback_job_type_field():
    """Remove job_type field from crawl_jobs table"""
    
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
        
        # Check if job_type column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'crawl_jobs' 
            AND COLUMN_NAME = 'job_type'
        """, (config['database'],))
        
        if not cursor.fetchone():
            print("WARNING: job_type column does not exist. Nothing to rollback.")
            return True
        
        # Drop the index first (if it exists)
        try:
            cursor.execute("ALTER TABLE crawl_jobs DROP INDEX idx_job_type")
            print("[SUCCESS] Dropped index idx_job_type")
        except pymysql.Error as e:
            if "doesn't exist" in str(e).lower():
                print("Index idx_job_type does not exist, skipping...")
            else:
                print(f"Warning: Could not drop index idx_job_type: {e}")
        
        # Remove job_type column
        cursor.execute("ALTER TABLE crawl_jobs DROP COLUMN job_type")
        print("[SUCCESS] Removed job_type column from crawl_jobs table")
        
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

def check_column_exists():
    """Check if job_type column exists"""
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
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'crawl_jobs' 
            AND COLUMN_NAME = 'job_type'
        """, (config['database'],))
        
        result = cursor.fetchone()
        return result is not None
        
    except pymysql.Error as err:
        print(f"Error checking column existence: {err}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == '__main__':
    print("Rolling back job_type field from crawl_jobs table...")
    print("=" * 60)
    
    # Check if column exists
    if not check_column_exists():
        print("WARNING: job_type column does not exist. Nothing to rollback.")
    else:
        # Remove the column
        if rollback_job_type_field():
            print("\nSUCCESS: Rollback completed successfully!")
            print("The job_type field has been removed from crawl_jobs table.")
        else:
            print("\nERROR: Rollback failed!")
            print("Please check the error messages above and try again.")