"""baseline

Revision ID: 4f2ed2e7dc57
Revises:
Create Date: 2026-07-23 22:36:09.624026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f2ed2e7dc57'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Gerada originalmente como no-op via `alembic stamp head` contra um banco de
    dev que já tinha essas tabelas (criadas antes do Alembic entrar no projeto,
    via Base.metadata.create_all) — funcionava local, mas quebrava num banco
    novo do zero. Reescrita aqui com os CREATE TABLE reais das 9 tabelas que
    existiam nesse ponto da história (as migrações seguintes já têm DDL real
    e continuam válidas em cima desta)."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('plan', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
    )
    op.create_table(
        'modules',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('icon_url', sa.String(), nullable=True),
        sa.Column('requires_plan', sa.String(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
    )
    op.create_table(
        'apps',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('template_type', sa.String(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('modules', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'app_configs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('module_id', sa.Integer(), sa.ForeignKey('modules.id'), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'form_submissions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('module_name', sa.String(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'app_users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('auth_provider', sa.String(), nullable=True),
        sa.Column('facebook_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('app_id', 'email', name='uq_app_users_app_id_email'),
    )

    op.create_table(
        'module_categories',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('module_name', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=True),
    )

    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False, unique=True),
        sa.Column('p256dh', sa.String(), nullable=False),
        sa.Column('auth', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'module_items',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('module_name', sa.String(), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('module_categories.id'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('module_items')
    op.drop_table('push_subscriptions')
    op.drop_table('module_categories')
    op.drop_table('app_users')
    op.drop_table('form_submissions')
    op.drop_table('app_configs')
    op.drop_table('apps')
    op.drop_table('modules')
    op.drop_table('users')
