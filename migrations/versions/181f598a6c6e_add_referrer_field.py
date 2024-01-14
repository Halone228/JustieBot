"""add referrer field

Revision ID: 181f598a6c6e
Revises: 264390378c28
Create Date: 2024-01-14 20:30:34.282571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '181f598a6c6e'
down_revision: Union[str, None] = '264390378c28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user_info_table',
        sa.Column('referrer', sa.ForeignKey('users_table.id'))
    )
    op.create_table(
        'referrers_table',
        sa.Column('referrer_id', sa.ForeignKey('users_table.id'), primary_key=True, nullable=True),
        sa.Column('referral_id', sa.ForeignKey('users_table.id'))
    )


def downgrade() -> None:
    pass
