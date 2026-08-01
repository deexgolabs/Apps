"""add table_reservations table

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-31 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'table_reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.Integer(), nullable=False),
        sa.Column('end_user_id', sa.Integer(), nullable=True),
        sa.Column('customer_name', sa.String(), nullable=False),
        sa.Column('customer_phone', sa.String(), nullable=False),
        sa.Column('party_size', sa.Integer(), nullable=False),
        sa.Column('reservation_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('table_number', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id']),
        sa.ForeignKeyConstraint(['end_user_id'], ['app_users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_table_reservations_id'), 'table_reservations', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_table_reservations_id'), table_name='table_reservations')
    op.drop_table('table_reservations')
