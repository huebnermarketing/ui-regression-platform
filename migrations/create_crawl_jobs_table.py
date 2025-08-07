"""
Migration script to create crawl_jobs table for Phase 2.5
Run this script to add crawl job tracking functionality
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_crawl_jobs_table():
    """Create the crawl_jobs table"""
    
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
        
        # Create crawl_jobs table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS crawl_jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            status ENUM('pending', 'running', 'completed', 'failed') NOT NULL DEFAULT 'pending',
            total_pages INT NOT NULL DEFAULT 0,
            started_at DATETIME NULL,
            completed_at DATETIME NULL,
            error_message TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_status (status),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(create_table_query)
        print("✓ Created crawl_jobs table")
        
        # Commit the changes
        connection.commit()
        print("✓ Migration completed successfully!")
        
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

def check_table_exists():
    """Check if crawl_jobs table already exists"""
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
        
        cursor.execute("SHOW TABLES LIKE 'crawl_jobs'")
        result = cursor.fetchone()
        
        return result is not None
        
    except pymysql.Error as err:
        print(f"Error checking table existence: {err}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == '__main__':
    print("Phase 2.5: Creating crawl_jobs table...")
    print("=" * 50)
    
    # Check if table already exists
    if check_table_exists():
        print("WARNING: crawl_jobs table already exists. Skipping migration.")
    else:
        # Create the table
        if create_crawl_jobs_table():
            print("\nSUCCESS: Migration completed successfully!")
            print("The crawl_jobs table has been created and is ready to use.")
        else:
            print("\nERROR: Migration failed!")
            print("Please check the error messages above and try again.")