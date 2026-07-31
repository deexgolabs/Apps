"""add webhook_subscriptions table

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-31 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('event', sa.String(), nullable=False),
        sa.Column('secret', sa.String(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_webhook_subscriptions_id'), 'webhook_subscriptions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_webhook_subscriptions_id'), table_name='webhook_subscriptions')
    op.drop_table('webhook_subscriptions')
