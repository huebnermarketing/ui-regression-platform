"""
Migration to add new job status values for find difference workflow
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

def add_find_diff_job_statuses():
    """Add new enum values for find difference workflow"""
    engine = get_db_engine()
    if not engine:
        return False
    
    try:
        with engine.connect() as connection:
            print("Adding new job status values for find difference workflow...")
            
            # Add new enum values to crawl_job_status
            alter_query = text("""
            ALTER TABLE crawl_jobs
            MODIFY COLUMN status ENUM(
                'pending',
                'Crawling',
                'Crawled',
                'Job Failed',
                'finding_difference',
                'ready',
                'diff_failed'
            ) NOT NULL DEFAULT 'pending'
            """)
            
            connection.execute(alter_query)
            connection.commit()
            
            print("Successfully added new job status values:")
            print("   - finding_difference")
            print("   - ready")
            print("   - diff_failed")
            
            return True
            
    except Exception as e:
        print(f"Error adding job status values: {e}")
        return False

if __name__ == "__main__":
    print("Starting migration to add find difference job statuses...")
    success = add_find_diff_job_statuses()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")