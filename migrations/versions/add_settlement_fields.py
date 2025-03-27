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
    # Helper function to check if a column exists
    def column_exists(table_name, column_name):
        conn = op.get_bind()
        insp = sa.inspect(conn)
        
        # Check if table exists first
        if not conn.dialect.has_table(conn, table_name):
            return False
            
        columns = [c['name'] for c in insp.get_columns(table_name)]
        return column_name in columns

    # Add missing fields to settlements table if they don't exist
    if not column_exists('settlements', 'prosperity'):
        op.add_column('settlements', sa.Column('prosperity', sa.Integer(), nullable=True, server_default='5'))
    
    if not column_exists('settlements', 'biome'):
        op.add_column('settlements', sa.Column('biome', sa.String(30), nullable=True, server_default='plains'))


def downgrade():
    # Helper function to check if a column exists
    def column_exists(table_name, column_name):
        conn = op.get_bind()
        insp = sa.inspect(conn)
        
        # Check if table exists first
        if not conn.dialect.has_table(conn, table_name):
            return False
            
        columns = [c['name'] for c in insp.get_columns(table_name)]
        return column_name in columns
    
    # Drop the added columns if they exist
    if column_exists('settlements', 'prosperity'):
        op.drop_column('settlements', 'prosperity')
    
    if column_exists('settlements', 'biome'):
        op.drop_column('settlements', 'biome')