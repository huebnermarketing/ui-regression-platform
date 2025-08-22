#!/usr/bin/env python3
"""
Migration: Add 'finding_difference' and 'ready' values to find_diff_status enum
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import db

def run_migration():
    """Add new enum values to find_diff_status column"""
    # Import app after setting up path
    from app import app
    
    with app.app_context():
        try:
            print("Adding new enum values to find_diff_status column...")
            
            # For MySQL, we need to alter the enum type
            db.session.execute(text("""
                ALTER TABLE project_pages
                MODIFY COLUMN find_diff_status
                ENUM('pending', 'capturing', 'captured', 'diffing', 'finding_difference', 'ready', 'completed', 'failed', 'no_baseline')
                NOT NULL DEFAULT 'pending'
            """))
            
            db.session.commit()
            print("Successfully added 'finding_difference' and 'ready' values to find_diff_status enum")
            
            # Verify the change
            result = db.session.execute(text("""
                SHOW COLUMNS FROM project_pages LIKE 'find_diff_status'
            """)).fetchone()
            
            if result:
                print(f"find_diff_status column definition: {result[1]}")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    run_migration()