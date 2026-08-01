"""add auto coupons (birthday/first purchase/referral)

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-08-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f8a9b0c1d2e3'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('app_users', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column('app_users', sa.Column('referral_code', sa.String(), nullable=True))
    op.add_column('app_users', sa.Column('referred_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_app_users_referred_by_id', 'app_users', 'app_users', ['referred_by_id'], ['id']
    )

    op.add_column('coupons', sa.Column('end_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_coupons_end_user_id', 'coupons', 'app_users', ['end_user_id'], ['id']
    )

    op.create_table(
        'auto_coupon_rules',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('trigger', sa.String(), nullable=False),
        sa.Column('discount_type', sa.String(), nullable=False, server_default='percent'),
        sa.Column('discount_value', sa.Float(), nullable=False),
        sa.Column('valid_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('app_id', 'trigger', name='uq_auto_coupon_rules_app_id_trigger'),
    )

    op.create_table(
        'auto_coupon_issuances',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), nullable=False),
        sa.Column('end_user_id', sa.Integer(), sa.ForeignKey('app_users.id'), nullable=False),
        sa.Column('trigger', sa.String(), nullable=False),
        sa.Column('period_key', sa.String(), nullable=False),
        sa.Column('coupon_id', sa.Integer(), sa.ForeignKey('coupons.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('app_id', 'end_user_id', 'trigger', 'period_key', name='uq_auto_coupon_issuance'),
    )


def downgrade() -> None:
    op.drop_table('auto_coupon_issuances')
    op.drop_table('auto_coupon_rules')

    op.drop_constraint('fk_coupons_end_user_id', 'coupons', type_='foreignkey')
    op.drop_column('coupons', 'end_user_id')

    op.drop_constraint('fk_app_users_referred_by_id', 'app_users', type_='foreignkey')
    op.drop_column('app_users', 'referred_by_id')
    op.drop_column('app_users', 'referral_code')
    op.drop_column('app_users', 'birth_date')
