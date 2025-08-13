"""
Rollback script to remove timestamped run support fields
This undoes the changes made by add_timestamped_runs.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def rollback_timestamped_runs():
    """Remove timestamped run columns from project_pages table"""
    
    from models import db
    from sqlalchemy import text
    
    try:
        with db.engine.connect() as conn:
            print("Rolling back timestamped run support columns...")
            
            # List of columns to remove
            columns_to_remove = [
                'current_run_id', 
                'baseline_run_id', 
                'find_diff_status', 
                'last_run_at',
                'diff_status_desktop', 
                'diff_status_tablet', 
                'diff_status_mobile',
                'diff_error_desktop', 
                'diff_error_tablet', 
                'diff_error_mobile'
            ]
            
            # Remove columns one by one
            for i, column in enumerate(columns_to_remove, 1):
                try:
                    conn.execute(text(f"ALTER TABLE project_pages DROP COLUMN IF EXISTS {column}"))
                    print(f"  [{i:2d}/{len(columns_to_remove)}] Removed: {column}")
                except Exception as e:
                    print(f"  [{i:2d}/{len(columns_to_remove)}] Warning: Could not remove column {column}: {e}")
            
            conn.commit()
            print(f"\n[SUCCESS] Removed timestamped run support columns from project_pages table")
            return True
            
    except Exception as e:
        print(f"Error during rollback: {e}")
        return False

if __name__ == '__main__':
    from app import app
    
    print("Rolling back timestamped run support from project_pages table...")
    print("=" * 60)
    
    with app.app_context():
        if rollback_timestamped_runs():
            print("\nSUCCESS: Timestamped runs rollback completed successfully!")
            print("All timestamped run support columns have been removed from project_pages table.")
        else:
            print("\nERROR: Rollback failed!")
            print("Please check the error messages above and try again.")