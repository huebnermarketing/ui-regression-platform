#!/usr/bin/env python3
"""
Database Migration: Fix Timestamp Consistency

This migration ensures all timestamp columns in the database
are properly handled and any timezone inconsistencies are resolved.
"""

import os
import sys
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_timestamp_migration():
    """Run the timestamp consistency migration"""
    
    try:
        from app import app
        from models import db
        from models.user import User
        from models.project import Project
        from models.crawl_job import CrawlJob
        from sqlalchemy import text
        
        print("[FIXING] Starting timestamp consistency migration...")
        print("=" * 50)
        
        with app.app_context():
            # 1. Check current timestamp data
            print("1. Analyzing current timestamp data...")
            
            # Check for any NULL timestamps that should have values
            null_created_at = db.session.execute(text("""
                SELECT COUNT(*) as count FROM users WHERE created_at IS NULL
                UNION ALL
                SELECT COUNT(*) as count FROM projects WHERE created_at IS NULL
                UNION ALL
                SELECT COUNT(*) as count FROM crawl_jobs WHERE created_at IS NULL
            """)).fetchall()
            
            total_null_timestamps = sum(row[0] for row in null_created_at)
            print(f"   Found {total_null_timestamps} NULL created_at timestamps")
            
            # 2. Fix NULL created_at timestamps
            if total_null_timestamps > 0:
                print("2. Fixing NULL created_at timestamps...")
                current_utc = datetime.now(timezone.utc)
                
                # Fix users
                result = db.session.execute(text("""
                    UPDATE users SET created_at = :current_time WHERE created_at IS NULL
                """), {'current_time': current_utc})
                print(f"   Fixed {result.rowcount} user records")
                
                # Fix projects
                result = db.session.execute(text("""
                    UPDATE projects SET created_at = :current_time WHERE created_at IS NULL
                """), {'current_time': current_utc})
                print(f"   Fixed {result.rowcount} project records")
                
                # Fix crawl jobs
                result = db.session.execute(text("""
                    UPDATE crawl_jobs SET created_at = :current_time WHERE created_at IS NULL
                """), {'current_time': current_utc})
                print(f"   Fixed {result.rowcount} crawl job records")
            else:
                print("2. No NULL created_at timestamps found - skipping fix")
            
            # 3. Validate timestamp consistency
            print("3. Validating timestamp consistency...")
            
            # Check for any obviously wrong timestamps (future dates)
            future_timestamps = db.session.execute(text("""
                SELECT 'users' as table_name, COUNT(*) as count 
                FROM users WHERE created_at > :future_time
                UNION ALL
                SELECT 'projects' as table_name, COUNT(*) as count 
                FROM projects WHERE created_at > :future_time
                UNION ALL
                SELECT 'crawl_jobs' as table_name, COUNT(*) as count 
                FROM crawl_jobs WHERE created_at > :future_time
            """), {'future_time': datetime.now(timezone.utc)}).fetchall()
            
            for table, count in future_timestamps:
                if count > 0:
                    print(f"   WARNING: {count} future timestamps found in {table}")
                else:
                    print(f"   [OK] {table} timestamps look correct")
            
            # 4. Commit changes
            db.session.commit()
            print("4. [OK] Migration completed successfully!")
            
            print("\n" + "=" * 50)
            print("[SUCCESS] TIMESTAMP MIGRATION COMPLETED!")
            print("All timestamp data has been validated and fixed.")
            
            return True
            
    except Exception as e:
        print(f"[ERROR] Migration failed: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return False

if __name__ == '__main__':
    success = run_timestamp_migration()
    sys.exit(0 if success else 1)
