"""
Migration to add phase-specific timestamp fields to crawl_jobs table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_engine():
    """Get database engine"""
    try:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')
        db_user = os.getenv('DB_USER', 'root')
        db_password = os.getenv('DB_PASSWORD', '')
        db_port = int(os.getenv('DB_PORT', 3306))
        
        # URL encode the password to handle special characters
        from urllib.parse import quote_plus
        encoded_password = quote_plus(db_password)
        database_url = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(database_url)
        return engine
    except Exception as e:
        print(f"Error creating database engine: {e}")
        return None

def add_phase_timestamps():
    """Add phase-specific timestamp fields to crawl_jobs table"""
    engine = get_db_engine()
    if not engine:
        return False
    
    try:
        with engine.connect() as connection:
            print("Adding phase-specific timestamp fields to crawl_jobs table...")
            
            # Check if columns already exist
            check_query = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'crawl_jobs' 
            AND COLUMN_NAME IN ('crawl_started_at', 'crawl_completed_at', 'fd_started_at', 'fd_completed_at')
            """)
            
            existing_columns = connection.execute(check_query).fetchall()
            existing_column_names = [row[0] for row in existing_columns]
            
            # Add columns that don't exist
            columns_to_add = [
                ('crawl_started_at', 'DATETIME NULL COMMENT "Timestamp when crawl phase started"'),
                ('crawl_completed_at', 'DATETIME NULL COMMENT "Timestamp when crawl phase completed"'),
                ('fd_started_at', 'DATETIME NULL COMMENT "Timestamp when find difference phase started"'),
                ('fd_completed_at', 'DATETIME NULL COMMENT "Timestamp when find difference phase completed"')
            ]
            
            for column_name, column_def in columns_to_add:
                if column_name not in existing_column_names:
                    alter_query = text(f"ALTER TABLE crawl_jobs ADD COLUMN {column_name} {column_def}")
                    connection.execute(alter_query)
                    print(f"   - Added column: {column_name}")
                else:
                    print(f"   - Column already exists: {column_name}")
            
            connection.commit()
            
            # Migrate existing data: copy started_at to crawl_started_at and completed_at to crawl_completed_at
            # for jobs that are already completed
            print("Migrating existing timestamp data...")
            
            migrate_query = text("""
            UPDATE crawl_jobs 
            SET crawl_started_at = started_at,
                crawl_completed_at = CASE 
                    WHEN status IN ('Crawled', 'ready', 'diff_failed') THEN completed_at 
                    ELSE NULL 
                END
            WHERE crawl_started_at IS NULL
            """)
            
            result = connection.execute(migrate_query)
            connection.commit()
            
            print(f"   - Migrated {result.rowcount} existing records")
            print("Successfully added phase timestamp fields!")
            
            return True
            
    except Exception as e:
        print(f"Error adding phase timestamp fields: {e}")
        return False

if __name__ == "__main__":
    print("Starting migration to add phase timestamp fields...")
    success = add_phase_timestamps()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")