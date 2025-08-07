"""
Migration: Add 'paused' status to crawl_jobs table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app import app, db

def upgrade():
    """Add 'paused' status to the status enum"""
    with app.app_context():
        # For MySQL, we need to modify the enum to include 'paused'
        with db.engine.connect() as connection:
            connection.execute(text("""
                ALTER TABLE crawl_jobs
                MODIFY COLUMN status ENUM('pending', 'running', 'paused', 'completed', 'failed')
                NOT NULL DEFAULT 'pending'
            """))
            connection.commit()
        
        print("SUCCESS: Added 'paused' status to crawl_jobs.status enum")

def downgrade():
    """Remove 'paused' status from the status enum"""
    with app.app_context():
        # First, update any paused jobs to pending
        with db.engine.connect() as connection:
            connection.execute(text("""
                UPDATE crawl_jobs SET status = 'pending' WHERE status = 'paused'
            """))
            
            # Then remove 'paused' from the enum
            connection.execute(text("""
                ALTER TABLE crawl_jobs
                MODIFY COLUMN status ENUM('pending', 'running', 'completed', 'failed')
                NOT NULL DEFAULT 'pending'
            """))
            connection.commit()
        
        print("SUCCESS: Removed 'paused' status from crawl_jobs.status enum")

if __name__ == '__main__':
    print("Running migration: Add 'paused' status to crawl_jobs table")
    upgrade()
    print("Migration completed successfully!")