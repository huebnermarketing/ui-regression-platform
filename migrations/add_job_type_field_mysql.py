"""
Migration script to add job_type field to crawl_jobs table
Run this script to add job type tracking functionality
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_job_type_field():
    """Add job_type field to crawl_jobs table"""
    
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
        
        # Check if job_type column already exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'crawl_jobs' 
            AND COLUMN_NAME = 'job_type'
        """, (config['database'],))
        
        if cursor.fetchone():
            print("WARNING: job_type column already exists. Skipping migration.")
            return True
        
        # Add job_type column
        alter_table_query = """
        ALTER TABLE crawl_jobs 
        ADD COLUMN job_type VARCHAR(20) NOT NULL DEFAULT 'crawl' 
        AFTER status
        """
        
        cursor.execute(alter_table_query)
        print("[SUCCESS] Added job_type column to crawl_jobs table")
        
        # Add index for job_type for better query performance
        add_index_query = """
        ALTER TABLE crawl_jobs 
        ADD INDEX idx_job_type (job_type)
        """
        
        cursor.execute(add_index_query)
        print("[SUCCESS] Added index for job_type column")
        
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

def check_column_exists():
    """Check if job_type column already exists"""
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
    print("Adding job_type field to crawl_jobs table...")
    print("=" * 50)
    
    # Check if column already exists
    if check_column_exists():
        print("WARNING: job_type column already exists. Skipping migration.")
    else:
        # Add the column
        if add_job_type_field():
            print("\nSUCCESS: Migration completed successfully!")
            print("The job_type field has been added to crawl_jobs table.")
        else:
            print("\nERROR: Migration failed!")
            print("Please check the error messages above and try again.")