"""add referral fields to users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-30 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('referral_code', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_referral_code'), 'users', ['referral_code'], unique=True)
    op.add_column('users', sa.Column('referred_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_referred_by_id_users', 'users', 'users', ['referred_by_id'], ['id'])
    op.add_column('users', sa.Column('bonus_app_slots', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('referral_reward_granted', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'referral_reward_granted')
    op.drop_column('users', 'bonus_app_slots')
    op.drop_constraint('fk_users_referred_by_id_users', 'users', type_='foreignkey')
    op.drop_column('users', 'referred_by_id')
    op.drop_index(op.f('ix_users_referral_code'), table_name='users')
    op.drop_column('users', 'referral_code')
