"""merge_all_heads

Revision ID: 8a10babf05ea
Revises: 213CD232, add_settlement_fields, create_roles_system, create_task_tables
Create Date: 2025-03-26 22:39:24.099567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a10babf05ea'
down_revision: Union[str, None] = ('213CD232', 'add_settlement_fields', 'create_roles_system', 'create_task_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
