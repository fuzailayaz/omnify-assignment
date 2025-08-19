"""Add timestamps to bookings

Revision ID: add_timestamps_to_bookings
Revises: 
Create Date: 2025-08-18 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = 'add_timestamps_to_bookings'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add created_at column with server_default
    op.add_column('bookings', 
                 sa.Column('created_at', 
                          sa.DateTime(timezone=True), 
                          server_default=func.now(),
                          nullable=False))
    
    # Add updated_at column with server_default and onupdate
    op.add_column('bookings',
                 sa.Column('updated_at',
                          sa.DateTime(timezone=True),
                          server_default=func.now(),
                          onupdate=func.now(),
                          nullable=False))

def downgrade():
    op.drop_column('bookings', 'updated_at')
    op.drop_column('bookings', 'created_at')
