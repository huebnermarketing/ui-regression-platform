"""
Migration to add visual diff fields to project_pages table
"""

from sqlalchemy import text
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db

def upgrade():
    """Add diff fields to project_pages table"""
    
    # Add new diff columns
    db.session.execute(text("""
        ALTER TABLE project_pages
        ADD COLUMN diff_image_path TEXT NULL,
        ADD COLUMN diff_raw_image_path TEXT NULL,
        ADD COLUMN diff_mismatch_pct DECIMAL(6,3) NULL,
        ADD COLUMN diff_pixels_changed INT NULL,
        ADD COLUMN diff_bounding_boxes JSON NULL,
        ADD COLUMN diff_generated_at DATETIME NULL,
        ADD COLUMN diff_error TEXT NULL
    """))
    
    # Update the status enum to include new diff statuses
    db.session.execute(text("""
        ALTER TABLE project_pages
        MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_screenshot', 'screenshot_complete', 'screenshot_failed', 'ready_for_diff', 'diff_pending', 'diff_running', 'diff_generated', 'diff_failed')
        NOT NULL DEFAULT 'pending'
    """))
    
    db.session.commit()
    
    print("Added diff fields to project_pages table")

def downgrade():
    """Remove diff fields from project_pages table"""
    
    # Remove the new columns
    db.session.execute(text("""
        ALTER TABLE project_pages
        DROP COLUMN diff_image_path,
        DROP COLUMN diff_raw_image_path,
        DROP COLUMN diff_mismatch_pct,
        DROP COLUMN diff_pixels_changed,
        DROP COLUMN diff_bounding_boxes,
        DROP COLUMN diff_generated_at,
        DROP COLUMN diff_error
    """))
    
    # Revert the status enum
    db.session.execute(text("""
        ALTER TABLE project_pages
        MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_screenshot', 'screenshot_complete', 'screenshot_failed', 'ready_for_diff', 'diff_generated')
        NOT NULL DEFAULT 'pending'
    """))
    
    db.session.commit()
    
    print("Removed diff fields from project_pages table")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        upgrade()