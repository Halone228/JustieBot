"""create user_info table

Revision ID: 02a6e09b53a4
Revises: 
Create Date: 2023-12-28 23:44:00.944317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02a6e09b53a4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    users = op.create_table(
        'users_table',
        sa.Column('id', sa.BigInteger(), nullable=False, primary_key=True)
    )
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT user_id FROM user_table")).fetchall()
    op.bulk_insert(
        users,
        [{'id': i[0]} for i in res]
    )
    op.create_table(
        'user_info_table',
        sa.Column('user_id', sa.ForeignKey(users.columns[0]), primary_key=True),
        sa.Column('username', sa.Text, nullable=True),
        sa.Column('first_name', sa.Text, nullable=True),
        sa.Column('last_name', sa.Text, nullable=True)
    )
    op.rename_table('user_table', 'user_points_table')
    op.create_foreign_key(
        'user_id',
        'user_points_table',
        'users_table',
        ['user_id'],
        ['id']
    )


def downgrade() -> None:
    pass
