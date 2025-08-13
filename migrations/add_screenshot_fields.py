"""
Migration to add screenshot fields to project_pages table
"""

from sqlalchemy import text
from models import db

def upgrade():
    """Add screenshot fields to project_pages table"""
    
    # Add new columns
    db.engine.execute(text("""
        ALTER TABLE project_pages 
        ADD COLUMN staging_screenshot_path TEXT NULL,
        ADD COLUMN production_screenshot_path TEXT NULL
    """))
    
    # Update the status enum to include new screenshot statuses
    db.engine.execute(text("""
        ALTER TABLE project_pages
        MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_screenshot', 'screenshot_complete', 'screenshot_failed', 'ready_for_diff', 'diff_generated')
        NOT NULL DEFAULT 'pending'
    """))
    
    print("Added screenshot fields to project_pages table")

def downgrade():
    """Remove screenshot fields from project_pages table"""
    
    # Remove the new columns
    db.engine.execute(text("""
        ALTER TABLE project_pages 
        DROP COLUMN staging_screenshot_path,
        DROP COLUMN production_screenshot_path
    """))
    
    # Revert the status enum
    db.engine.execute(text("""
        ALTER TABLE project_pages 
        MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_diff') 
        NOT NULL DEFAULT 'pending'
    """))
    
    print("Removed screenshot fields from project_pages table")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        upgrade()