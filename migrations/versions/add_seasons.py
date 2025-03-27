"""add seasons

Revision ID: add_seasons_to_world
Revises: trader_journey_fields
Create Date: 2025-04-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = 'add_seasons_to_world'
down_revision = 'trader_journey_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add season tracking to existing worlds table
    # Check if columns exist before adding them
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("worlds")}
    
    # Only add columns if they don't exist
    if "current_season" not in columns:
        op.add_column('worlds', sa.Column('current_season', sa.String(10), nullable=False, server_default='spring'))
    if "day_of_season" not in columns:
        op.add_column('worlds', sa.Column('day_of_season', sa.Integer(), nullable=False, server_default='1'))
    if "days_per_season" not in columns:
        op.add_column('worlds', sa.Column('days_per_season', sa.Integer(), nullable=False, server_default='30'))
    if "current_year" not in columns:
        op.add_column('worlds', sa.Column('current_year', sa.Integer(), nullable=False, server_default='1'))
    
    # Create seasons configuration table if it doesn't exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'seasons' not in existing_tables:
        op.create_table(
            'seasons',
            sa.Column('season_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(10), nullable=False),
            sa.Column('display_name', sa.String(30), nullable=False),
            sa.Column('next_season', sa.String(10), nullable=False),
            sa.Column('resource_modifiers', JSONB, nullable=False),
            sa.Column('travel_modifier', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('color_hex', sa.String(7), nullable=False, server_default='#FFFFFF'),
            sa.PrimaryKeyConstraint('season_id')
        )
    
    # Insert default seasons if the table is empty
    from sqlalchemy import text
    conn = op.get_bind()
    seasons_count = conn.execute(text("SELECT COUNT(*) FROM seasons")).scalar()
    
    if seasons_count == 0:
        op.execute("""
        INSERT INTO seasons (name, display_name, next_season, resource_modifiers, travel_modifier, description, color_hex)
        VALUES
            ('spring', 'Spring', 'summer', '{"wood": 1.0, "food": 1.2, "stone": 0.9, "ore": 0.9, "herbs": 1.3}', 1.0, 'The growing season. Food and herbs are plentiful.', '#76FF7A'),
            ('summer', 'Summer', 'autumn', '{"wood": 1.1, "food": 1.1, "stone": 1.2, "ore": 1.2, "herbs": 1.0}', 1.2, 'Hot and dry. Mining and construction are efficient.', '#FFCF40'),
            ('autumn', 'Autumn', 'winter', '{"wood": 1.2, "food": 1.0, "stone": 1.1, "ore": 1.0, "herbs": 0.8}', 1.0, 'Harvest time. Wood gathering is most effective.', '#FF9A3D'),
            ('winter', 'Winter', 'spring', '{"wood": 0.7, "food": 0.6, "stone": 0.7, "ore": 0.8, "herbs": 0.5}', 0.7, 'Cold and harsh. All resource production slows. Travel is difficult.', '#A0E9FF');
        """)


def downgrade():
    # Drop seasons table
    op.drop_table('seasons')
    
    # Remove season tracking from worlds table
    op.drop_column('worlds', 'current_season')
    op.drop_column('worlds', 'day_of_season')
    op.drop_column('worlds', 'days_per_season')
    op.drop_column('worlds', 'current_year')