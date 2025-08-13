"""
Rollback script to remove visual diff fields from project_pages table
This undoes the changes made by add_diff_fields.py
"""

from sqlalchemy import text
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db

def rollback_diff_fields():
    """Remove diff fields from project_pages table"""
    
    try:
        with app.app_context():
            print("Rolling back diff fields from project_pages table...")
            
            # Remove the new columns
            db.session.execute(text("""
                ALTER TABLE project_pages
                DROP COLUMN IF EXISTS diff_image_path,
                DROP COLUMN IF EXISTS diff_raw_image_path,
                DROP COLUMN IF EXISTS diff_mismatch_pct,
                DROP COLUMN IF EXISTS diff_pixels_changed,
                DROP COLUMN IF EXISTS diff_bounding_boxes,
                DROP COLUMN IF EXISTS diff_generated_at,
                DROP COLUMN IF EXISTS diff_error
            """))
            
            print("Removed diff columns from project_pages table")
            
            # Revert the status enum to remove diff-related statuses
            db.session.execute(text("""
                ALTER TABLE project_pages
                MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_screenshot', 'screenshot_complete', 'screenshot_failed', 'ready_for_diff', 'diff_generated')
                NOT NULL DEFAULT 'pending'
            """))
            
            print("Reverted status ENUM to remove diff-related statuses")
            
            db.session.commit()
            print("[SUCCESS] Rollback of diff fields completed successfully!")
            
    except Exception as e:
        print(f"Error during rollback: {e}")
        db.session.rollback()
        return False
    
    return True

if __name__ == '__main__':
    print("Rolling back diff fields from project_pages table...")
    print("=" * 60)
    
    if rollback_diff_fields():
        print("\nSUCCESS: Diff fields rollback completed successfully!")
        print("All diff-related columns have been removed from project_pages table.")
    else:
        print("\nERROR: Rollback failed!")
        print("Please check the error messages above and try again.")