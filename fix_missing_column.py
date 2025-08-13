#!/usr/bin/env python3
"""
Fix missing diff_raw_image_path column
"""

from sqlalchemy import text
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db

def fix_missing_column():
    """Add only the missing diff_raw_image_path column"""
    
    with app.app_context():
        try:
            # Check if column exists
            result = db.session.execute(text("SHOW COLUMNS FROM project_pages LIKE 'diff_raw_image_path'"))
            exists = len(list(result)) > 0
            
            if not exists:
                print("Adding missing diff_raw_image_path column...")
                db.session.execute(text("ALTER TABLE project_pages ADD COLUMN diff_raw_image_path TEXT NULL"))
                db.session.commit()
                print("Successfully added diff_raw_image_path column")
            else:
                print("diff_raw_image_path column already exists")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_missing_column()