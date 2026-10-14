from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c31f76a284e9'
down_revision: Union[str, Sequence[str], None] = 'b82a61f409cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'outbox_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_outbox_events_created_at', 'outbox_events', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_outbox_events_created_at', table_name='outbox_events')
    op.drop_table('outbox_events')
