"""
Migration to add timestamped run support for Find Difference workflow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def upgrade():
    """Add new columns for timestamped runs and enhanced multi-viewport support"""
    
    from models import db
    from sqlalchemy import text
    
    # Add new columns to project_pages table
    with db.engine.connect() as conn:
        # Run ID for grouping captures/diffs by timestamp
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN current_run_id VARCHAR(20) NULL
        """))
        
        # Baseline run ID for comparison
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN baseline_run_id VARCHAR(20) NULL
        """))
        
        # Enhanced status tracking
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN find_diff_status ENUM(
                'pending', 'capturing', 'captured', 'diffing', 'completed', 'failed', 'no_baseline'
            ) DEFAULT 'pending'
        """))
        
        # Last run timestamp
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN last_run_at DATETIME NULL
        """))
        
        # Multi-viewport diff status
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN diff_status_desktop ENUM('pending', 'processing', 'completed', 'failed', 'no_baseline') DEFAULT 'pending'
        """))
        
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN diff_status_tablet ENUM('pending', 'processing', 'completed', 'failed', 'no_baseline') DEFAULT 'pending'
        """))
        
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN diff_status_mobile ENUM('pending', 'processing', 'completed', 'failed', 'no_baseline') DEFAULT 'pending'
        """))
        
        # Error messages per viewport
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN diff_error_desktop TEXT NULL
        """))
        
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN diff_error_tablet TEXT NULL
        """))
        
        conn.execute(text("""
            ALTER TABLE project_pages
            ADD COLUMN diff_error_mobile TEXT NULL
        """))
        
        print("Added timestamped run support columns to project_pages table")

def downgrade():
    """Remove timestamped run columns"""
    
    from models import db
    from sqlalchemy import text
    
    with db.engine.connect() as conn:
        # Remove new columns
        columns_to_remove = [
            'current_run_id', 'baseline_run_id', 'find_diff_status', 'last_run_at',
            'diff_status_desktop', 'diff_status_tablet', 'diff_status_mobile',
            'diff_error_desktop', 'diff_error_tablet', 'diff_error_mobile'
        ]
        
        for column in columns_to_remove:
            try:
                conn.execute(text(f"ALTER TABLE project_pages DROP COLUMN {column}"))
            except Exception as e:
                print(f"Warning: Could not remove column {column}: {e}")
        
        print("Removed timestamped run support columns from project_pages table")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        upgrade()