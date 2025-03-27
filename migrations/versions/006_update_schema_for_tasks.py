"""Add trader journey fields

Revision ID: trader_journey_fields
Revises: 2c1153fe1e62
Create Date: 2025-03-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '213CD232'
down_revision = 'trader_journey_fields'
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

    # Add new columns to traders table if they don't exist
    if not column_exists('traders', 'can_move'):
        op.add_column('traders', sa.Column('can_move', sa.String(), nullable=True))
    
    if not column_exists('traders', 'active_task_id'):
        op.add_column('traders', sa.Column('active_task_id', sa.String(), nullable=True))
    
    if not column_exists('area_encounters', 'requires_assistance'):
        op.add_column('area_encounters', sa.Column('requires_assistance', sa.Integer(), nullable=True))
    
    if not column_exists('area_encounters', 'task_id'):
        op.add_column('area_encounters', sa.Column('task_id', sa.Integer(), nullable=True))

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
    
    # Remove columns added in the upgrade function if they exist
    if column_exists('traders', 'can_move'):
        op.drop_column('traders', 'can_move')
    
    if column_exists('traders', 'active_task_id'):
        op.drop_column('traders', 'active_task_id')
    
    if column_exists('area_encounters', 'requires_assistance'):
        op.drop_column('area_encounters', 'requires_assistance')
    
    if column_exists('area_encounters', 'task_id'):
        op.drop_column('area_encounters', 'task_id')