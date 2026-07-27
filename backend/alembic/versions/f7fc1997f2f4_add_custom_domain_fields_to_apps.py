"""add custom domain fields to apps

Revision ID: f7fc1997f2f4
Revises: e734fee16743
Create Date: 2026-07-27 13:42:47.823943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7fc1997f2f4'
down_revision: Union[str, Sequence[str], None] = 'e734fee16743'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('apps', sa.Column('custom_domain', sa.String(), nullable=True))
    op.add_column('apps', sa.Column('custom_domain_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('apps', sa.Column('custom_domain_verification_token', sa.String(), nullable=True))
    op.create_unique_constraint('uq_apps_custom_domain', 'apps', ['custom_domain'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_apps_custom_domain', 'apps', type_='unique')
    op.drop_column('apps', 'custom_domain_verification_token')
    op.drop_column('apps', 'custom_domain_verified')
    op.drop_column('apps', 'custom_domain')
