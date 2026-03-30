"""baseline: stamp existing schema

Revision ID: 0001
Revises: 
Create Date: 2026-03-29 20:25:13.816056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline stamp — no changes.

    All tables already exist via db.create_all().
    Run `alembic stamp 0001` on existing databases to mark this as applied.
    Future migrations will auto-generate diffs against models.py.
    """
    pass


def downgrade() -> None:
    """Cannot downgrade from baseline."""
    pass
