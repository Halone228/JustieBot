"""delete deprecated columns user_points:

Revision ID: 264390378c28
Revises: 02a6e09b53a4
Create Date: 2023-12-29 01:30:53.852068

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '264390378c28'
down_revision: Union[str, None] = '02a6e09b53a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('user_points_table', 'expire_date')
    op.drop_column('user_points_table', 'notified')
    op.drop_column('user_points_table', 'in_group')
    op.drop_column('user_points_table', 'messages')


def downgrade() -> None:
    pass
