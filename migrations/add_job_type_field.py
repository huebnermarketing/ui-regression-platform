"""Add job_type field to crawl_jobs table

Revision ID: add_job_type_field
Revises: 
Create Date: 2025-01-08 16:46:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_job_type_field'
down_revision = None
depends_on = None

def upgrade():
    """Add job_type field to crawl_jobs table"""
    
    # Create the enum type first
    job_type_enum = sa.Enum('crawl', 'screenshot', 'diff', 'find_difference', name='job_type_enum')
    job_type_enum.create(op.get_bind())
    
    # Add the job_type column with default value 'crawl'
    op.add_column('crawl_jobs', sa.Column('job_type', job_type_enum, nullable=False, server_default='crawl'))
    
    print("Added job_type field to crawl_jobs table")

def downgrade():
    """Remove job_type field from crawl_jobs table"""
    
    # Drop the column
    op.drop_column('crawl_jobs', 'job_type')
    
    # Drop the enum type
    job_type_enum = sa.Enum('crawl', 'screenshot', 'diff', 'find_difference', name='job_type_enum')
    job_type_enum.drop(op.get_bind())
    
    print("Removed job_type field from crawl_jobs table")