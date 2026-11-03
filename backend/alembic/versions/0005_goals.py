"""goals

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-03 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('goals',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('label_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.Enum('normal', 'emergency_fund', name='goal_type', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('target_amount', sa.Numeric(precision=14, scale=2, asdecimal=True), nullable=True),
    sa.Column('months_of_expenses', sa.SmallInteger(), nullable=True),
    sa.Column('deadline', sa.Date(), nullable=True),
    sa.Column('manual_progress', sa.Numeric(precision=14, scale=2, asdecimal=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("(type = 'normal' AND target_amount > 0 AND months_of_expenses IS NULL) OR (type = 'emergency_fund' AND target_amount IS NULL AND months_of_expenses BETWEEN 1 AND 24)", name=op.f('ck_goals_target_matches_type')),
    sa.ForeignKeyConstraint(['label_id'], ['labels.id'], name=op.f('fk_goals_label_id_labels'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_goals_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_goals'))
    )
    op.create_index('ix_goals_user_id', 'goals', ['user_id'], unique=False)
    op.create_index('uq_goals_label_active', 'goals', ['label_id'], unique=True, postgresql_where=sa.text('deleted_at IS NULL AND completed_at IS NULL'))


def downgrade() -> None:
    op.drop_table('goals')
