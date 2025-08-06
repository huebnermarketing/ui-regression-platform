#!/usr/bin/env python3
"""
Database migration script to add page_name and last_crawled columns to project_pages table
"""

import os
import sys
from dotenv import load_dotenv
import pymysql
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')
    
    try:
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"""
        SELECT COUNT(*) as count 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = '{table_name}' 
        AND COLUMN_NAME = '{column_name}'
    """)
    result = cursor.fetchone()
    return result['count'] > 0

def migrate_database():
    """Run the database migration"""
    print("Starting database migration...")
    
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database. Exiting.")
        return False
    
    try:
        with connection.cursor() as cursor:
            # Check if page_name column exists
            if not check_column_exists(cursor, 'project_pages', 'page_name'):
                print("Adding page_name column...")
                cursor.execute("""
                    ALTER TABLE project_pages 
                    ADD COLUMN page_name VARCHAR(500) NULL 
                    AFTER path
                """)
                print("+ page_name column added successfully")
            else:
                print("+ page_name column already exists")
            
            # Check if last_crawled column exists
            if not check_column_exists(cursor, 'project_pages', 'last_crawled'):
                print("Adding last_crawled column...")
                cursor.execute("""
                    ALTER TABLE project_pages
                    ADD COLUMN last_crawled DATETIME NULL
                    AFTER status
                """)
                print("+ last_crawled column added successfully")
            else:
                print("+ last_crawled column already exists")
            
            # Update existing records with default last_crawled value
            cursor.execute("""
                UPDATE project_pages 
                SET last_crawled = created_at 
                WHERE last_crawled IS NULL
            """)
            
            # Commit the changes
            connection.commit()
            print("+ Migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()
    
    return True

if __name__ == "__main__":
    print("UI Regression Platform - Database Migration")
    print("=" * 50)
    
    success = migrate_database()
    
    if success:
        print("\n[SUCCESS] Migration completed successfully!")
        print("The database schema has been updated with:")
        print("  - page_name column (VARCHAR(500)) for storing page titles")
        print("  - last_crawled column (DATETIME) for tracking crawl times")
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)