"""
Migration script to add 'pending' status to crawl_job_status enum
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db
from models.crawl_job import CrawlJob
from sqlalchemy import text

def add_pending_status():
    """Add 'pending' status to crawl_job_status enum"""
    # Import app after setting up path
    from app import app
    
    with app.app_context():
        try:
            print("Adding 'pending' status to crawl_job_status enum...")
            
            # For MySQL, we need to modify the enum
            db.session.execute(text("""
                ALTER TABLE crawl_jobs 
                MODIFY COLUMN status ENUM('pending', 'Crawling', 'Crawled', 'Job Failed') 
                NOT NULL DEFAULT 'pending'
            """))
            
            db.session.commit()
            print("Successfully added 'pending' status to enum")
            
            # Verify the change
            result = db.session.execute(text("""
                SHOW COLUMNS FROM crawl_jobs LIKE 'status'
            """)).fetchone()
            
            if result:
                print(f"Status column definition: {result[1]}")
            
        except Exception as e:
            print(f"Error adding pending status: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    add_pending_status()