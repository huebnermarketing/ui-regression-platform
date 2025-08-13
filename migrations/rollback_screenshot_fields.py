"""
Rollback script to remove screenshot fields from project_pages table
This undoes the changes made by add_screenshot_fields.py
"""

from sqlalchemy import text
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db

def rollback_screenshot_fields():
    """Remove screenshot fields from project_pages table"""
    
    try:
        with app.app_context():
            print("Rolling back screenshot fields from project_pages table...")
            
            # Remove the screenshot columns
            db.session.execute(text("""
                ALTER TABLE project_pages 
                DROP COLUMN IF EXISTS staging_screenshot_path,
                DROP COLUMN IF EXISTS production_screenshot_path
            """))
            
            print("Removed screenshot columns from project_pages table")
            
            # Revert the status enum to remove screenshot-related statuses
            db.session.execute(text("""
                ALTER TABLE project_pages 
                MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_diff') 
                NOT NULL DEFAULT 'pending'
            """))
            
            print("Reverted status ENUM to remove screenshot-related statuses")
            
            db.session.commit()
            print("[SUCCESS] Rollback of screenshot fields completed successfully!")
            
    except Exception as e:
        print(f"Error during rollback: {e}")
        db.session.rollback()
        return False
    
    return True

if __name__ == '__main__':
    print("Rolling back screenshot fields from project_pages table...")
    print("=" * 60)
    
    if rollback_screenshot_fields():
        print("\nSUCCESS: Screenshot fields rollback completed successfully!")
        print("All screenshot-related columns have been removed from project_pages table.")
    else:
        print("\nERROR: Rollback failed!")
        print("Please check the error messages above and try again.")