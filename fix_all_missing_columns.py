#!/usr/bin/env python3
"""
Fix all missing diff columns in project_pages table
"""

from sqlalchemy import text
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db

def fix_all_missing_columns():
    """Add all missing diff columns"""
    
    # List of all diff columns that should exist
    diff_columns = [
        ('diff_image_path', 'TEXT NULL'),
        ('diff_raw_image_path', 'TEXT NULL'),
        ('diff_mismatch_pct', 'DECIMAL(6,3) NULL'),
        ('diff_pixels_changed', 'INT NULL'),
        ('diff_bounding_boxes', 'JSON NULL'),
        ('diff_generated_at', 'DATETIME NULL'),
        ('diff_error', 'TEXT NULL')
    ]
    
    with app.app_context():
        try:
            # Get existing columns
            result = db.session.execute(text("SHOW COLUMNS FROM project_pages"))
            existing_columns = [row[0] for row in result]
            print(f"Existing columns: {existing_columns}")
            
            # Check which diff columns are missing
            missing_columns = []
            for col_name, col_def in diff_columns:
                if col_name not in existing_columns:
                    missing_columns.append((col_name, col_def))
            
            if missing_columns:
                print(f"Missing columns: {[col[0] for col in missing_columns]}")
                
                # Add missing columns one by one
                for col_name, col_def in missing_columns:
                    print(f"Adding column: {col_name}")
                    db.session.execute(text(f"ALTER TABLE project_pages ADD COLUMN {col_name} {col_def}"))
                
                # Update the status enum to include all diff statuses
                print("Updating status enum...")
                db.session.execute(text("""
                    ALTER TABLE project_pages 
                    MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_screenshot', 'screenshot_complete', 'screenshot_failed', 'ready_for_diff', 'diff_pending', 'diff_running', 'diff_generated', 'diff_failed') 
                    NOT NULL DEFAULT 'pending'
                """))
                
                db.session.commit()
                print("Successfully added all missing diff columns")
            else:
                print("All diff columns already exist")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_all_missing_columns()