"""
Rollback script to remove 'paused' status from crawl_jobs table
This undoes the changes made by add_paused_status.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app import app, db

def rollback_paused_status():
    """Remove 'paused' status from the status enum"""
    try:
        with app.app_context():
            print("Rolling back 'paused' status from crawl_jobs table...")
            
            with db.engine.connect() as connection:
                # First, update any paused jobs to pending
                result = connection.execute(text("""
                    UPDATE crawl_jobs SET status = 'pending' WHERE status = 'paused'
                """))
                
                updated_rows = result.rowcount
                if updated_rows > 0:
                    print(f"Updated {updated_rows} paused jobs to pending status")
                
                # Then remove 'paused' from the enum
                connection.execute(text("""
                    ALTER TABLE crawl_jobs
                    MODIFY COLUMN status ENUM('pending', 'running', 'completed', 'failed')
                    NOT NULL DEFAULT 'pending'
                """))
                
                connection.commit()
            
            print("[SUCCESS] Removed 'paused' status from crawl_jobs.status enum")
            return True
            
    except Exception as e:
        print(f"Error during rollback: {e}")
        return False

if __name__ == '__main__':
    print("Rolling back 'paused' status from crawl_jobs table...")
    print("=" * 60)
    
    if rollback_paused_status():
        print("\nSUCCESS: Paused status rollback completed successfully!")
        print("The 'paused' status has been removed from crawl_jobs table.")
    else:
        print("\nERROR: Rollback failed!")
        print("Please check the error messages above and try again.")