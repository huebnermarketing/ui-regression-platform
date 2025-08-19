#!/usr/bin/env python3
"""
Standalone migration script to update crawl_jobs table with new columns for Jobs History feature
"""

import pymysql
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

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

def migrate_crawl_jobs():
    """Add new columns to crawl_jobs table and update existing data"""
    
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database. Exiting.")
        return False
    
    try:
        cursor = connection.cursor()
        
        print("Connected to database successfully")
        
        # Add job_number column if it doesn't exist
        if not check_column_exists(cursor, 'crawl_jobs', 'job_number'):
            print("Adding job_number column...")
            cursor.execute("""
                ALTER TABLE crawl_jobs 
                ADD COLUMN job_number INT NOT NULL DEFAULT 1
            """)
            connection.commit()
            print("+ job_number column added")
        else:
            print("+ job_number column already exists")
        
        # Add updated_at column if it doesn't exist
        if not check_column_exists(cursor, 'crawl_jobs', 'updated_at'):
            print("Adding updated_at column...")
            cursor.execute("""
                ALTER TABLE crawl_jobs 
                ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            """)
            connection.commit()
            print("+ updated_at column added")
        else:
            print("+ updated_at column already exists")
        
        # First, expand the status column to accommodate longer values
        print("Expanding status column...")
        cursor.execute("ALTER TABLE crawl_jobs MODIFY COLUMN status VARCHAR(20) NOT NULL")
        connection.commit()
        print("+ Status column expanded")
        
        # Update status values to new format
        print("Updating status values...")
        cursor.execute("""
            UPDATE crawl_jobs
            SET status = CASE
                WHEN status = 'pending' THEN 'Crawling'
                WHEN status = 'running' THEN 'Crawling'
                WHEN status = 'completed' THEN 'Crawled'
                WHEN status = 'failed' THEN 'Job Failed'
                WHEN status = 'paused' THEN 'Crawling'
                ELSE status
            END
        """)
        connection.commit()
        print("+ Status values updated")
        
        # Set proper job_number for existing records (per project)
        print("Setting job_number for existing records...")
        cursor.execute("SELECT DISTINCT project_id FROM crawl_jobs ORDER BY project_id")
        projects_with_jobs = cursor.fetchall()
        
        for (project_id,) in projects_with_jobs:
            # Get all jobs for this project ordered by created_at
            cursor.execute("""
                SELECT id FROM crawl_jobs 
                WHERE project_id = %s 
                ORDER BY created_at ASC
            """, (project_id,))
            jobs = cursor.fetchall()
            
            # Update job_number sequentially
            for i, (job_id,) in enumerate(jobs, 1):
                cursor.execute("""
                    UPDATE crawl_jobs 
                    SET job_number = %s 
                    WHERE id = %s
                """, (i, job_id))
        
        connection.commit()
        print("+ job_number values set for existing records")
        
        # Set updated_at to appropriate timestamp for existing records
        print("Setting updated_at for existing records...")
        cursor.execute("""
            UPDATE crawl_jobs 
            SET updated_at = COALESCE(completed_at, started_at, created_at)
            WHERE updated_at IS NULL OR updated_at = '1970-01-01 00:00:00'
        """)
        connection.commit()
        print("+ updated_at values set for existing records")
        
        print("\n[SUCCESS] Migration completed successfully!")
        
        # Show final table structure
        cursor.execute("DESCRIBE crawl_jobs")
        print("\nFinal table structure:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} {row[2]} {row[3]} {row[4]} {row[5]}")
        
        # Show sample data
        cursor.execute("SELECT id, project_id, job_number, status, updated_at FROM crawl_jobs LIMIT 5")
        sample_data = cursor.fetchall()
        if sample_data:
            print("\nSample data:")
            for row in sample_data:
                print(f"  ID: {row[0]}, Project: {row[1]}, Job#: {row[2]}, Status: {row[3]}, Updated: {row[4]}")
                
    except Exception as e:
        print(f"X Migration failed: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            connection.close()
            print("Database connection closed")
    
    return True

if __name__ == "__main__":
    print("PixelPulse - CrawlJob Migration")
    print("=" * 50)
    
    success = migrate_crawl_jobs()
    
    if success:
        print("\n[SUCCESS] Migration completed successfully!")
        print("The crawl_jobs table has been updated with:")
        print("  - job_number column (INT) for incremental job IDs per project")
        print("  - updated_at column (DATETIME) for tracking status changes")
        print("  - Updated status values to match Jobs History specification")
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)