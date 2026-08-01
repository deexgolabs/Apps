"""add abandoned_carts table

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-08-01 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, Sequence[str], None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'abandoned_carts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.Integer(), nullable=False),
        sa.Column('end_user_id', sa.Integer(), nullable=False),
        sa.Column('module_name', sa.String(), nullable=False),
        sa.Column('items', sa.JSON(), nullable=True),
        sa.Column('subtotal', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
        sa.ForeignKeyConstraint(['end_user_id'], ['app_users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('app_id', 'end_user_id', 'module_name', name='uq_abandoned_carts_app_user_module'),
    )
    op.create_index(op.f('ix_abandoned_carts_id'), 'abandoned_carts', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_abandoned_carts_id'), table_name='abandoned_carts')
    op.drop_table('abandoned_carts')
