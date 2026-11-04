from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd72e8a916b30'
down_revision: Union[str, Sequence[str], None] = 'c31f76a284e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'adaptations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('resume_id', sa.UUID(), nullable=False),
        sa.Column('vacancy_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(16), server_default='pending', nullable=False),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'running', 'done', 'failed')", name='ck_adaptations_status'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id']),
        sa.ForeignKeyConstraint(['vacancy_id'], ['vacancies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_adaptations_user_id', 'adaptations', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_adaptations_user_id', table_name='adaptations')
    op.drop_table('adaptations')
