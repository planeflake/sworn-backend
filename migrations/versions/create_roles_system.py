"""create roles system

Revision ID: create_roles_system
Revises: add_seasons_to_world
Create Date: 2025-04-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = 'create_roles_system'
down_revision = 'add_seasons_to_world'
branch_labels = None
depends_on = None

def upgrade():
    # Helper function to check if a table exists
    def table_exists(table_name):
        conn = op.get_bind()
        return conn.dialect.has_table(conn, table_name)
    
    # Helper function to check if a column exists
    def column_exists(table_name, column_name):
        conn = op.get_bind()
        if not table_exists(table_name):
            return False
        
        insp = sa.inspect(conn)
        columns = [c['name'] for c in insp.get_columns(table_name)]
        return column_name in columns
    
    # Create roles table - defines available roles
    if not table_exists('roles'):
        op.create_table(
            'roles',
            sa.Column('role_id', UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column('role_code', sa.String(50), nullable=False, unique=True),
            sa.Column('role_name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text),
            sa.Column('attribute_schema', JSONB), # JSON schema defining required attributes
            sa.Column('required_skills', JSONB), # Skills needed to gain this role
            sa.Column('role_benefits', JSONB), # Benefits gained from this role
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
        )
        
        # Insert default roles only if we just created the table
        op.execute("""
        INSERT INTO roles (role_code, role_name, description, required_skills, attribute_schema)
        VALUES 
        ('trader', 'Trader', 'Travels between settlements buying and selling goods', 
         '{"trading": 10, "negotiation": 5}',
         '{"type": "object", "properties": {"cart_capacity": {"type": "number"}, "cart_health": {"type": "number"}, "gold": {"type": "number"}, "inventory": {"type": "object"}, "journey": {"type": "object"}, "preferences": {"type": "object"}}}'),
        
        ('blacksmith', 'Blacksmith', 'Crafts metal items and tools', 
         '{"smithing": 20, "metallurgy": 10}',
         '{"type": "object", "properties": {"forge_level": {"type": "number"}, "specialties": {"type": "array"}, "quality_modifier": {"type": "number"}}}'),
         
        ('healer', 'Healer', 'Treats wounds and illnesses', 
         '{"medicine": 15, "herbalism": 10}',
         '{"type": "object", "properties": {"remedies_known": {"type": "array"}, "treatment_quality": {"type": "number"}}}')
        """)
    
    # Create character_roles table - assigns roles to NPCs or players
    if not table_exists('character_roles'):
        op.create_table(
            'character_roles',
            sa.Column('character_role_id', UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column('character_id', UUID, nullable=False), # Can be NPC or player
            sa.Column('character_type', sa.String(20), nullable=False), # 'npc' or 'player'
            sa.Column('role_id', UUID, nullable=False),
            sa.Column('level', sa.Integer, nullable=False, server_default='1'),
            sa.Column('attributes', JSONB), # Role-specific attributes
            sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
            sa.Column('gained_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='CASCADE')
        )
        
        # Add index for faster lookups
        op.create_index('idx_character_roles_lookup', 'character_roles', 
                       ['character_id', 'character_type', 'is_active'])
    
    # Create comprehensive skills table if it doesn't exist
    if not table_exists('skills'):
        op.create_table(
            'skills',
            sa.Column('skill_id', UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column('skill_code', sa.String(50), nullable=False, unique=True),
            sa.Column('skill_name', sa.String(100), nullable=False),
            sa.Column('category', sa.String(50)),
            sa.Column('description', sa.Text),
            sa.Column('max_level', sa.Integer, server_default='100'),
            sa.Column('xp_curve', JSONB), # How XP requirements scale
            sa.Column('effects', JSONB), # Effects at different levels
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
        )
    
    # Create character_skills table (more structured than current JSON)
    if not table_exists('character_skills'):
        op.create_table(
            'character_skills',
            sa.Column('character_skill_id', UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column('character_id', UUID, nullable=False),
            sa.Column('character_type', sa.String(20), nullable=False), # 'npc' or 'player'
            sa.Column('skill_id', UUID, nullable=False),
            sa.Column('level', sa.Integer, nullable=False, server_default='0'),
            sa.Column('xp', sa.Integer, nullable=False, server_default='0'),
            sa.Column('last_used', sa.DateTime),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['skill_id'], ['skills.skill_id'], ondelete='CASCADE')
        )
        
        # Create index for faster skill lookups
        op.create_index('idx_character_skills_lookup', 'character_skills', 
                       ['character_id', 'character_type'])
    
    # Add location tracking for NPCs (for dynamic movement) if columns don't exist
    if table_exists('npcs'):
        if not column_exists('npcs', 'current_location_type'):
            op.add_column('npcs', sa.Column('current_location_type', sa.String(20)))
        if not column_exists('npcs', 'current_location_id'):
            op.add_column('npcs', sa.Column('current_location_id', UUID))
        if not column_exists('npcs', 'destination_location_type'):
            op.add_column('npcs', sa.Column('destination_location_type', sa.String(20)))
        if not column_exists('npcs', 'destination_location_id'):
            op.add_column('npcs', sa.Column('destination_location_id', UUID))

def downgrade():
    # Helper function to check if a table exists
    def table_exists(table_name):
        conn = op.get_bind()
        return conn.dialect.has_table(conn, table_name)
    
    # Helper function to check if a column exists
    def column_exists(table_name, column_name):
        conn = op.get_bind()
        if not table_exists(table_name):
            return False
        
        insp = sa.inspect(conn)
        columns = [c['name'] for c in insp.get_columns(table_name)]
        return column_name in columns
    
    # Drop indexes and tables if they exist
    if table_exists('character_skills'):
        try:
            op.drop_index('idx_character_skills_lookup')
        except:
            pass
        op.drop_table('character_skills')
    
    if table_exists('skills'):
        op.drop_table('skills')
    
    if table_exists('character_roles'):
        try:
            op.drop_index('idx_character_roles_lookup')
        except:
            pass
        op.drop_table('character_roles')
    
    if table_exists('roles'):
        op.drop_table('roles')
    
    # Drop columns if they exist
    if table_exists('npcs'):
        if column_exists('npcs', 'current_location_type'):
            op.drop_column('npcs', 'current_location_type')
        if column_exists('npcs', 'current_location_id'):
            op.drop_column('npcs', 'current_location_id')
        if column_exists('npcs', 'destination_location_type'):
            op.drop_column('npcs', 'destination_location_type')
        if column_exists('npcs', 'destination_location_id'):
            op.drop_column('npcs', 'destination_location_id')