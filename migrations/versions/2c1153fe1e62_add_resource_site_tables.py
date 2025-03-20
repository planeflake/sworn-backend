"""Add resource site tables

Revision ID: 2c1153fe1e62
Revises: 
Create Date: 2025-03-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c1153fe1e62'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create ResourceSiteTypes table
    op.create_table('resource_site_types',
        sa.Column('site_type_id', sa.String(), nullable=False),
        sa.Column('theme_id', sa.String(), nullable=True),
        sa.Column('site_code', sa.String(), nullable=False),
        sa.Column('site_name', sa.String(), nullable=False),
        sa.Column('site_category', sa.String(), nullable=True),
        sa.Column('primary_resource_type_id', sa.String(), nullable=True),
        sa.Column('secondary_resource_types', sa.String(), nullable=True),
        sa.Column('compatible_area_types', sa.String(), nullable=True),
        sa.Column('rarity', sa.Float(), nullable=True),
        sa.Column('potential_stages', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('site_type_id')
    )
    
    # Create ResourceSites table
    op.create_table('resource_sites',
        sa.Column('site_id', sa.String(), nullable=False),
        sa.Column('settlement_id', sa.String(), nullable=True),
        sa.Column('site_type_id', sa.String(), nullable=True),
        sa.Column('current_stage', sa.String(), nullable=False),
        sa.Column('depletion_level', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('development_level', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('production_multiplier', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('discovery_date', sa.DateTime(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('associated_building_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('site_id')
    )

    # Add foreign key constraints  
    op.create_foreign_key('fk_resource_sites_site_type', 'resource_sites', 'resource_site_types', ['site_type_id'], ['site_type_id'])
    op.create_foreign_key('fk_resource_sites_settlement', 'resource_sites', 'settlements', ['settlement_id'], ['settlement_id'])
    op.create_foreign_key('fk_resource_sites_building', 'resource_sites', 'settlement_buildings', ['associated_building_id'], ['settlement_building_id'])


def downgrade():
    op.drop_constraint('fk_resource_sites_building', 'resource_sites', type_='foreignkey')
    op.drop_constraint('fk_resource_sites_settlement', 'resource_sites', type_='foreignkey')
    op.drop_constraint('fk_resource_sites_site_type', 'resource_sites', type_='foreignkey')
    op.drop_table('resource_sites')
    op.drop_table('resource_site_types')