"""Add timezone column to fitness_classes

Revision ID: add_timezone_to_fitness_classes
Revises: 
Create Date: 2025-08-18 13:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_timezone_to_fitness_classes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add timezone column with default value 'Asia/Kolkata'
    op.add_column('fitness_classes', 
                 sa.Column('timezone', 
                          sa.String(length=50), 
                          nullable=False, 
                          server_default='Asia/Kolkata'))

def downgrade():
    # Remove the timezone column if rolling back
    op.drop_column('fitness_classes', 'timezone')
