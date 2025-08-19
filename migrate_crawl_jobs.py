#!/usr/bin/env python3
"""
Migration script to update crawl_jobs table with new columns for Jobs History feature
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.crawl_job import CrawlJob
from sqlalchemy import text
from datetime import datetime

def migrate_crawl_jobs():
    """Add new columns to crawl_jobs table and update existing data"""
    
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("DESCRIBE crawl_jobs"))
            columns = [row[0] for row in result.fetchall()]
            
            print(f"Current columns: {columns}")
            
            # Add job_number column if it doesn't exist
            if 'job_number' not in columns:
                print("Adding job_number column...")
                db.session.execute(text("""
                    ALTER TABLE crawl_jobs 
                    ADD COLUMN job_number INT NOT NULL DEFAULT 1
                """))
                db.session.commit()
                print("✓ job_number column added")
            else:
                print("✓ job_number column already exists")
            
            # Add updated_at column if it doesn't exist
            if 'updated_at' not in columns:
                print("Adding updated_at column...")
                db.session.execute(text("""
                    ALTER TABLE crawl_jobs 
                    ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                """))
                db.session.commit()
                print("✓ updated_at column added")
            else:
                print("✓ updated_at column already exists")
            
            # Update status enum to include new values
            print("Updating status enum...")
            try:
                # First, update existing status values to new format
                db.session.execute(text("""
                    UPDATE crawl_jobs 
                    SET status = CASE 
                        WHEN status = 'pending' THEN 'Crawling'
                        WHEN status = 'running' THEN 'Crawling'
                        WHEN status = 'completed' THEN 'Crawled'
                        WHEN status = 'failed' THEN 'Job Failed'
                        WHEN status = 'paused' THEN 'Crawling'
                        ELSE status
                    END
                """))
                
                # Drop the old enum constraint and create new one
                db.session.execute(text("ALTER TABLE crawl_jobs MODIFY COLUMN status VARCHAR(20) NOT NULL"))
                db.session.commit()
                print("✓ Status values updated")
            except Exception as e:
                print(f"Status update warning (may be expected): {e}")
            
            # Set proper job_number for existing records (per project)
            print("Setting job_number for existing records...")
            projects_with_jobs = db.session.execute(text("""
                SELECT DISTINCT project_id FROM crawl_jobs ORDER BY project_id
            """)).fetchall()
            
            for (project_id,) in projects_with_jobs:
                # Get all jobs for this project ordered by created_at
                jobs = db.session.execute(text("""
                    SELECT id FROM crawl_jobs 
                    WHERE project_id = :project_id 
                    ORDER BY created_at ASC
                """), {'project_id': project_id}).fetchall()
                
                # Update job_number sequentially
                for i, (job_id,) in enumerate(jobs, 1):
                    db.session.execute(text("""
                        UPDATE crawl_jobs 
                        SET job_number = :job_number 
                        WHERE id = :job_id
                    """), {'job_number': i, 'job_id': job_id})
            
            db.session.commit()
            print("✓ job_number values set for existing records")
            
            # Set updated_at to created_at for existing records where updated_at is null
            print("Setting updated_at for existing records...")
            db.session.execute(text("""
                UPDATE crawl_jobs 
                SET updated_at = COALESCE(completed_at, started_at, created_at)
                WHERE updated_at IS NULL OR updated_at = '1970-01-01 00:00:00'
            """))
            db.session.commit()
            print("✓ updated_at values set for existing records")
            
            print("\n🎉 Migration completed successfully!")
            
            # Show final table structure
            result = db.session.execute(text("DESCRIBE crawl_jobs"))
            print("\nFinal table structure:")
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} {row[2]} {row[3]} {row[4]} {row[5]}")
                
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    print("Starting crawl_jobs table migration...")
    migrate_crawl_jobs()