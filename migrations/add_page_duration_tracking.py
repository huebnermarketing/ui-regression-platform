"""
Migration to add per-page duration tracking fields to project_pages table
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

def add_page_duration_tracking():
    """Add per-page duration tracking fields to project_pages table"""
    engine = get_db_engine()
    if not engine:
        return False
    
    try:
        with engine.connect() as connection:
            print("Adding per-page duration tracking fields to project_pages table...")
            
            # Check if columns already exist
            check_query = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'project_pages' 
            AND COLUMN_NAME IN ('duration', 'processing_started_at', 'processing_completed_at')
            """)
            
            existing_columns = connection.execute(check_query).fetchall()
            existing_column_names = [row[0] for row in existing_columns]
            
            # Add columns that don't exist
            columns_to_add = [
                ('duration', 'DECIMAL(8,3) NULL COMMENT "Duration in seconds for screenshot capture + diff generation"'),
                ('processing_started_at', 'DATETIME NULL COMMENT "Timestamp when processing started for this page"'),
                ('processing_completed_at', 'DATETIME NULL COMMENT "Timestamp when processing completed for this page"')
            ]
            
            for column_name, column_def in columns_to_add:
                if column_name not in existing_column_names:
                    alter_query = text(f"ALTER TABLE project_pages ADD COLUMN {column_name} {column_def}")
                    connection.execute(alter_query)
                    print(f"   - Added column: {column_name}")
                else:
                    print(f"   - Column already exists: {column_name}")
            
            connection.commit()
            print("Successfully added per-page duration tracking fields!")
            
            return True
            
    except Exception as e:
        print(f"Error adding per-page duration tracking fields: {e}")
        return False

if __name__ == "__main__":
    print("Starting migration to add per-page duration tracking...")
    success = add_page_duration_tracking()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")