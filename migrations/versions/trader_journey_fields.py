"""Add trader journey fields

Revision ID: trader_journey_fields
Revises: 2c1153fe1e62
Create Date: 2025-03-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'trader_journey_fields'
down_revision = '2c1153fe1e62'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to traders table
    op.add_column('traders', sa.Column('current_area_id', sa.String(), nullable=True))
    op.add_column('traders', sa.Column('journey_path', sa.String(), nullable=True))
    op.add_column('traders', sa.Column('path_position', sa.Integer(), nullable=True))
    op.add_column('traders', sa.Column('journey_progress', sa.Integer(), nullable=True))
    op.add_column('traders', sa.Column('journey_started', sa.DateTime(), nullable=True))
    op.add_column('traders', sa.Column('destination_settlement_name', sa.String(), nullable=True))
    
    # Also ensure destination_id is String type
    op.alter_column('traders', 'destination_id', 
                   existing_type=sa.Integer(),
                   type_=sa.String(),
                   existing_nullable=True)


def downgrade():
    # Remove columns
    op.drop_column('traders', 'current_area_id')
    op.drop_column('traders', 'journey_path')
    op.drop_column('traders', 'path_position')
    op.drop_column('traders', 'journey_progress')
    op.drop_column('traders', 'journey_started')
    op.drop_column('traders', 'destination_settlement_name')
    
    # Revert destination_id to Integer
    op.alter_column('traders', 'destination_id', 
                   existing_type=sa.String(),
                   type_=sa.Integer(),
                   existing_nullable=True)