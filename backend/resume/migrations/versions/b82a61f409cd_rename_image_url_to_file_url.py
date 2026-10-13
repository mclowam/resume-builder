from typing import Sequence, Union

from alembic import op


revision: str = 'b82a61f409cd'
down_revision: Union[str, Sequence[str], None] = '95dfb2606712'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('resumes', 'image_url', new_column_name='file_url')


def downgrade() -> None:
    op.alter_column('resumes', 'file_url', new_column_name='image_url')
