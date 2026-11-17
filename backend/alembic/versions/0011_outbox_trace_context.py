"""outbox trace context

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-17 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The trace of the request that wrote the event (traceparent), so the relay and
    # the consumers continue it. Empty when tracing is off.
    op.add_column(
        'outbox_events',
        sa.Column('trace_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('outbox_events', 'trace_context')
