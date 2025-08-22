"""Increase path length in project_pages

Revision ID: 4b2ceb563d21
Revises: 
Create Date: 2025-08-22 13:30:35.663785

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4b2ceb563d21'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('project_pages', schema=None) as batch_op:
        batch_op.alter_column('path',
               existing_type=mysql.VARCHAR(length=255),
               type_=sa.String(length=767),
               existing_nullable=False)

def downgrade():
    with op.batch_alter_table('project_pages', schema=None) as batch_op:
        batch_op.alter_column('path',
               existing_type=sa.String(length=767),
               type_=mysql.VARCHAR(length=255),
               existing_nullable=False)
    # ### end Alembic commands ###