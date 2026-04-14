"""fixed sql type error

Revision ID: 5ae962796e63
Revises: abf3134df78f
Create Date: 2026-04-14 16:51:49.903429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ae962796e63'
down_revision: Union[str, Sequence[str], None] = 'abf3134df78f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.execute("ALTER TABLE user_account ALTER COLUMN role DROP DEFAULT")
    sa.Enum("ADMIN", "USER", "MODERATOR", name="roleenum").create(op.get_bind())

    op.execute(
        "ALTER TABLE user_account ALTER COLUMN role TYPE roleenum USING UPPER(role)::roleenum"
    )
    op.execute(
        "ALTER TABLE user_account ALTER COLUMN role SET DEFAULT 'USER'::roleenum"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE user_account ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE user_account ALTER COLUMN role TYPE VARCHAR USING role::text"
    )
    op.execute("ALTER TABLE user_account ALTER COLUMN role SET DEFAULT 'user'")
    sa.Enum("ADMIN", "USER", "MODERATOR", name="roleenum").drop(op.get_bind())
