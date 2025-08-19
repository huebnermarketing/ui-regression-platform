"""
Database migration to add path component storage
Replaces full path storage with individual components for PathResolver
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


def upgrade():
    """Add component-based path storage columns"""
    
    # Add new columns to project_pages table for component storage
    op.add_column('project_pages', sa.Column('current_run_id', sa.String(20), nullable=True))
    op.add_column('project_pages', sa.Column('baseline_run_id', sa.String(20), nullable=True))
    
    # Add component storage columns (these will replace the full path columns)
    op.add_column('project_pages', sa.Column('page_slug', sa.String(255), nullable=True))
    
    # Add status tracking for each viewport
    op.add_column('project_pages', sa.Column('screenshot_status_desktop', sa.String(20), nullable=True, default='pending'))
    op.add_column('project_pages', sa.Column('screenshot_status_tablet', sa.String(20), nullable=True, default='pending'))
    op.add_column('project_pages', sa.Column('screenshot_status_mobile', sa.String(20), nullable=True, default='pending'))
    
    op.add_column('project_pages', sa.Column('diff_status_desktop', sa.String(20), nullable=True, default='pending'))
    op.add_column('project_pages', sa.Column('diff_status_tablet', sa.String(20), nullable=True, default='pending'))
    op.add_column('project_pages', sa.Column('diff_status_mobile', sa.String(20), nullable=True, default='pending'))
    
    # Add error tracking for each viewport
    op.add_column('project_pages', sa.Column('screenshot_error_desktop', sa.Text, nullable=True))
    op.add_column('project_pages', sa.Column('screenshot_error_tablet', sa.Text, nullable=True))
    op.add_column('project_pages', sa.Column('screenshot_error_mobile', sa.Text, nullable=True))
    
    op.add_column('project_pages', sa.Column('diff_error_desktop', sa.Text, nullable=True))
    op.add_column('project_pages', sa.Column('diff_error_tablet', sa.Text, nullable=True))
    op.add_column('project_pages', sa.Column('diff_error_mobile', sa.Text, nullable=True))
    
    # Add metrics for each viewport
    op.add_column('project_pages', sa.Column('diff_mismatch_pct_desktop', sa.Float, nullable=True))
    op.add_column('project_pages', sa.Column('diff_mismatch_pct_tablet', sa.Float, nullable=True))
    op.add_column('project_pages', sa.Column('diff_mismatch_pct_mobile', sa.Float, nullable=True))
    
    op.add_column('project_pages', sa.Column('diff_pixels_changed_desktop', sa.Integer, nullable=True))
    op.add_column('project_pages', sa.Column('diff_pixels_changed_tablet', sa.Integer, nullable=True))
    op.add_column('project_pages', sa.Column('diff_pixels_changed_mobile', sa.Integer, nullable=True))
    
    # Add timestamp for last processing
    op.add_column('project_pages', sa.Column('last_run_at', sa.DateTime, nullable=True))
    
    # Add overall find_diff_status to track the unified workflow
    op.add_column('project_pages', sa.Column('find_diff_status', sa.String(20), nullable=True, default='pending'))
    
    # Create indexes for better query performance
    op.create_index('idx_project_pages_current_run_id', 'project_pages', ['current_run_id'])
    op.create_index('idx_project_pages_baseline_run_id', 'project_pages', ['baseline_run_id'])
    op.create_index('idx_project_pages_page_slug', 'project_pages', ['page_slug'])
    op.create_index('idx_project_pages_find_diff_status', 'project_pages', ['find_diff_status'])
    
    # Populate page_slug for existing records using PathResolver logic
    connection = op.get_bind()
    
    # Import PathResolver logic for slugification
    import re
    import hashlib
    
    def slugify_page_path(page_path):
        """Slugify page path using same logic as PathResolver"""
        if not page_path:
            return 'home'
        
        # Remove leading/trailing slashes
        path = page_path.strip('/')
        
        # If empty path (root), use 'home'
        if not path:
            return 'home'
        
        # Convert to lowercase
        path = path.lower()
        
        # Replace slashes with underscores
        slug = path.replace('/', '_')
        
        # Replace special characters with underscores
        slug = re.sub(r'[^a-z0-9_-]', '_', slug)
        
        # Replace multiple underscores with single underscore
        slug = re.sub(r'_+', '_', slug)
        
        # Remove leading/trailing underscores
        slug = slug.strip('_')
        
        # Ensure it's not empty
        if not slug:
            return 'page'
        
        # Limit filename length
        max_length = 200
        if len(slug) > max_length:
            # Truncate and add hash for uniqueness
            hash_suffix = hashlib.md5(page_path.encode()).hexdigest()[:8]
            slug = slug[:max_length-9] + '_' + hash_suffix
        
        return slug
    
    # Update existing records with page_slug
    result = connection.execute(text("SELECT id, path FROM project_pages WHERE page_slug IS NULL"))
    for row in result:
        page_id = row[0]
        page_path = row[1] or ''
        page_slug = slugify_page_path(page_path)
        
        connection.execute(
            text("UPDATE project_pages SET page_slug = :page_slug WHERE id = :page_id"),
            {'page_slug': page_slug, 'page_id': page_id}
        )
    
    # Set default values for status columns
    connection.execute(text("""
        UPDATE project_pages 
        SET 
            screenshot_status_desktop = 'pending',
            screenshot_status_tablet = 'pending', 
            screenshot_status_mobile = 'pending',
            diff_status_desktop = 'pending',
            diff_status_tablet = 'pending',
            diff_status_mobile = 'pending',
            find_diff_status = 'pending'
        WHERE 
            screenshot_status_desktop IS NULL
    """))


def downgrade():
    """Remove component-based path storage columns"""
    
    # Drop indexes
    op.drop_index('idx_project_pages_find_diff_status', 'project_pages')
    op.drop_index('idx_project_pages_page_slug', 'project_pages')
    op.drop_index('idx_project_pages_baseline_run_id', 'project_pages')
    op.drop_index('idx_project_pages_current_run_id', 'project_pages')
    
    # Drop columns
    op.drop_column('project_pages', 'find_diff_status')
    op.drop_column('project_pages', 'last_run_at')
    
    op.drop_column('project_pages', 'diff_pixels_changed_mobile')
    op.drop_column('project_pages', 'diff_pixels_changed_tablet')
    op.drop_column('project_pages', 'diff_pixels_changed_desktop')
    
    op.drop_column('project_pages', 'diff_mismatch_pct_mobile')
    op.drop_column('project_pages', 'diff_mismatch_pct_tablet')
    op.drop_column('project_pages', 'diff_mismatch_pct_desktop')
    
    op.drop_column('project_pages', 'diff_error_mobile')
    op.drop_column('project_pages', 'diff_error_tablet')
    op.drop_column('project_pages', 'diff_error_desktop')
    
    op.drop_column('project_pages', 'screenshot_error_mobile')
    op.drop_column('project_pages', 'screenshot_error_tablet')
    op.drop_column('project_pages', 'screenshot_error_desktop')
    
    op.drop_column('project_pages', 'diff_status_mobile')
    op.drop_column('project_pages', 'diff_status_tablet')
    op.drop_column('project_pages', 'diff_status_desktop')
    
    op.drop_column('project_pages', 'screenshot_status_mobile')
    op.drop_column('project_pages', 'screenshot_status_tablet')
    op.drop_column('project_pages', 'screenshot_status_desktop')
    
    op.drop_column('project_pages', 'page_slug')
    op.drop_column('project_pages', 'baseline_run_id')
    op.drop_column('project_pages', 'current_run_id')