"""add sold auction status

Revision ID: 74eb3aa21eed
Revises: 93274da65cf0
Create Date: 2026-10-07 15:09:40.455879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74eb3aa21eed'
down_revision: Union[str, Sequence[str], None] = '93274da65cf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE auctionstatus ADD VALUE IF NOT EXISTS 'SOLD'")
        op.execute("""
        UPDATE auctions
        SET status = 'SOLD'
        WHERE status = 'ENDED'
          AND ended_at IS NOT NULL
          AND ended_at < end_date
          AND EXISTS (SELECT 1 FROM bids WHERE bids.auction_id = auctions.id)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
