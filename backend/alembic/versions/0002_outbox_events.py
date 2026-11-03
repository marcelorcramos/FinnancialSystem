"""outbox events and processed events

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('outbox_events',
    sa.Column('type', sa.String(length=100), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outbox_events'))
    )
    op.create_index('ix_outbox_events_pending', 'outbox_events', ['created_at'], unique=False, postgresql_where=sa.text('published_at IS NULL'))
    op.create_table('processed_events',
    sa.Column('consumer', sa.String(length=50), nullable=False),
    sa.Column('event_id', sa.Uuid(), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('consumer', 'event_id', name=op.f('pk_processed_events'))
    )


def downgrade() -> None:
    op.drop_table('processed_events')
    op.drop_index('ix_outbox_events_pending', table_name='outbox_events', postgresql_where=sa.text('published_at IS NULL'))
    op.drop_table('outbox_events')
