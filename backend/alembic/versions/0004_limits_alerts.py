"""limits and alerts

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('limits',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('label_id', sa.Uuid(), nullable=False),
    sa.Column('month_id', sa.Uuid(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=14, scale=2, asdecimal=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('amount > 0', name=op.f('ck_limits_amount_positive')),
    sa.ForeignKeyConstraint(['label_id'], ['labels.id'], name=op.f('fk_limits_label_id_labels'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['month_id'], ['months.id'], name=op.f('fk_limits_month_id_months'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_limits_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_limits'))
    )
    op.create_index('ix_limits_user_id', 'limits', ['user_id'], unique=False)
    op.create_index('uq_limits_label_default', 'limits', ['label_id'], unique=True, postgresql_where=sa.text('month_id IS NULL AND deleted_at IS NULL'))
    op.create_index('uq_limits_label_month', 'limits', ['label_id', 'month_id'], unique=True, postgresql_where=sa.text('month_id IS NOT NULL AND deleted_at IS NULL'))
    op.create_table('alerts',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('limit_id', sa.Uuid(), nullable=False),
    sa.Column('label_id', sa.Uuid(), nullable=False),
    sa.Column('month_id', sa.Uuid(), nullable=False),
    sa.Column('level', sa.Enum('warning', 'exceeded', name='alert_level', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('limit_amount', sa.Numeric(precision=14, scale=2, asdecimal=True), nullable=False),
    sa.Column('total', sa.Numeric(precision=14, scale=2, asdecimal=True), nullable=False),
    sa.Column('seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['label_id'], ['labels.id'], name=op.f('fk_alerts_label_id_labels'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['limit_id'], ['limits.id'], name=op.f('fk_alerts_limit_id_limits'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['month_id'], ['months.id'], name=op.f('fk_alerts_month_id_months'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_alerts_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_alerts'))
    )
    op.create_index('ix_alerts_user_created_at', 'alerts', ['user_id', 'created_at'], unique=False)
    op.create_index('uq_alerts_label_month_level', 'alerts', ['label_id', 'month_id', 'level'], unique=True)


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('limits')
