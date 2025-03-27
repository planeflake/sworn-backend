"""Create task system tables

Revision ID: create_task_tables
Revises: add_seasons_to_world
Create Date: 2025-05-10

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'create_task_tables'
down_revision = 'add_seasons_to_world'
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables already exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create task_types table if it doesn't exist
    if 'task_types' not in existing_tables:
        op.create_table(
            'task_types',
        sa.Column('task_type_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_xp', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('base_gold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('color_hex', sa.String(7), nullable=True, server_default='#FFFFFF'),
        sa.PrimaryKeyConstraint('task_type_id')
    )
    
    # Create tasks table if it doesn't exist
    if 'tasks' not in existing_tables:
        op.create_table(
            'tasks',
        sa.Column('task_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('task_type_id', UUID(as_uuid=True), nullable=False),
        sa.Column('world_id', UUID(as_uuid=True), nullable=False),
        sa.Column('character_id', UUID(as_uuid=True), nullable=True),
        sa.Column('location_id', sa.String(), nullable=True),
        sa.Column('target_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='available'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('completion_time', sa.DateTime(), nullable=True),
        sa.Column('requirements', JSONB, nullable=False, server_default='{}'),
        sa.Column('rewards', JSONB, nullable=False, server_default='{}'),
        sa.Column('task_data', JSONB, nullable=False, server_default='{}'),
        sa.Column('difficulty', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('repeatable', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['task_type_id'], ['task_types.task_type_id'], ),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.world_id'], ),
        sa.ForeignKeyConstraint(['character_id'], ['characters.character_id'], ),
        sa.PrimaryKeyConstraint('task_id')
    )
    
    # Create indices for faster lookups if tasks table exists
    if 'tasks' in existing_tables or 'tasks' not in existing_tables:  # Either we created it or it already existed
        # Check existing indices to avoid duplicates
        existing_indices = {idx['name'] for idx in inspector.get_indexes('tasks')}
        if 'ix_tasks_character_id' not in existing_indices:
            op.create_index(op.f('ix_tasks_character_id'), 'tasks', ['character_id'], unique=False)
        if 'ix_tasks_location_id' not in existing_indices:
            op.create_index(op.f('ix_tasks_location_id'), 'tasks', ['location_id'], unique=False)
        if 'ix_tasks_status' not in existing_indices:
            op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
        if 'ix_tasks_target_id' not in existing_indices:
            op.create_index(op.f('ix_tasks_target_id'), 'tasks', ['target_id'], unique=False)
        if 'ix_tasks_world_id' not in existing_indices:
            op.create_index(op.f('ix_tasks_world_id'), 'tasks', ['world_id'], unique=False)
    
    # Fix issues with the trader journey fields migration
    # Check if these columns exist first, since they might have been added by a previous migration
    conn = op.get_bind()
    
    # Check if traders table has can_move as string
    inspector = sa.inspect(conn)
    trader_columns = {col['name']: col for col in inspector.get_columns('traders')}
    area_encounter_columns = {col['name']: col for col in inspector.get_columns('area_encounters')}
    
    # If can_move exists and is wrong type, fix it
    if 'can_move' in trader_columns and trader_columns['can_move']['type'].python_type == str:
        op.drop_column('traders', 'can_move')
        op.add_column('traders', sa.Column('can_move', sa.Boolean(), nullable=False, server_default='true'))
    elif 'can_move' not in trader_columns:
        op.add_column('traders', sa.Column('can_move', sa.Boolean(), nullable=False, server_default='true'))
    
    # If active_task_id exists and is wrong type, fix it
    if 'active_task_id' in trader_columns and trader_columns['active_task_id']['type'].python_type == str:
        op.drop_column('traders', 'active_task_id')
        op.add_column('traders', sa.Column('active_task_id', UUID(as_uuid=True), nullable=True))
    elif 'active_task_id' not in trader_columns:
        op.add_column('traders', sa.Column('active_task_id', UUID(as_uuid=True), nullable=True))
    
    # If requires_assistance exists and is wrong type, fix it
    if 'requires_assistance' in area_encounter_columns and area_encounter_columns['requires_assistance']['type'].python_type == int:
        op.drop_column('area_encounters', 'requires_assistance')
        op.add_column('area_encounters', sa.Column('requires_assistance', sa.Boolean(), nullable=False, server_default='false'))
    elif 'requires_assistance' not in area_encounter_columns:
        op.add_column('area_encounters', sa.Column('requires_assistance', sa.Boolean(), nullable=False, server_default='false'))
    
    # If task_id exists and is wrong type, fix it
    if 'task_id' in area_encounter_columns and area_encounter_columns['task_id']['type'].python_type == int:
        op.drop_column('area_encounters', 'task_id')
        op.add_column('area_encounters', sa.Column('task_id', UUID(as_uuid=True), nullable=True))
    elif 'task_id' not in area_encounter_columns:
        op.add_column('area_encounters', sa.Column('task_id', UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraints only if both tables exist and tasks table exists
    if 'traders' in existing_tables and 'tasks' in existing_tables:
        # Check if constraint already exists
        try:
            op.create_foreign_key(
                'traders_active_task_id_fkey', 
                'traders', 'tasks',
                ['active_task_id'], ['task_id']
            )
        except Exception:
            # Constraint might already exist, skip
            pass
    
    if 'area_encounters' in existing_tables and 'tasks' in existing_tables:
        # Check if constraint already exists
        try:
            op.create_foreign_key(
                'area_encounters_task_id_fkey', 
                'area_encounters', 'tasks',
                ['task_id'], ['task_id']
            )
        except Exception:
            # Constraint might already exist, skip
            pass


def downgrade():
    # Try to drop foreign key constraints if they exist
    try:
        op.drop_constraint('traders_active_task_id_fkey', 'traders', type_='foreignkey')
    except Exception:
        pass
        
    try:
        op.drop_constraint('area_encounters_task_id_fkey', 'area_encounters', type_='foreignkey')
    except Exception:
        pass
    
    # Try to drop the task tables if they exist
    for idx in ['ix_tasks_world_id', 'ix_tasks_target_id', 'ix_tasks_status', 
                'ix_tasks_location_id', 'ix_tasks_character_id']:
        try:
            op.drop_index(op.f(idx), table_name='tasks')
        except Exception:
            pass
            
    try:
        op.drop_table('tasks')
    except Exception:
        pass
        
    try:
        op.drop_table('task_types')
    except Exception:
        pass
    
    # Try to drop columns from traders table if they exist
    try:
        op.drop_column('traders', 'can_move')
    except Exception:
        pass
        
    try:
        op.drop_column('traders', 'active_task_id')
    except Exception:
        pass
    
    # Try to drop columns from area_encounters table if they exist
    try:
        op.drop_column('area_encounters', 'requires_assistance')
    except Exception:
        pass
        
    try:
        op.drop_column('area_encounters', 'task_id')
    except Exception:
        pass