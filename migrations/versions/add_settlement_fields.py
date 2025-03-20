"""add_settlement_fields

Revision ID: add_settlement_fields
Revises: add_seasons_to_world
Create Date: 2025-03-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'add_settlement_fields'
down_revision = 'add_seasons_to_world'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing fields to settlements table
    op.add_column('settlements', sa.Column('prosperity', sa.Integer(), nullable=True, server_default='5'))
    op.add_column('settlements', sa.Column('biome', sa.String(30), nullable=True, server_default='plains'))


def downgrade():
    # Drop the added columns
    op.drop_column('settlements', 'prosperity')
    op.drop_column('settlements', 'biome')