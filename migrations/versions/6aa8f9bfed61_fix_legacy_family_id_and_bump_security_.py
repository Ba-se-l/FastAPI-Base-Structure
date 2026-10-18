"""fix legacy family_id and bump security_version

Revision ID: 6aa8f9bfed61
Revises: f2001b0d2995
Create Date: 2026-10-18 02:57:37.434503

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6aa8f9bfed61'
down_revision: Union[str, Sequence[str], None] = 'f2001b0d2995'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Give each legacy session its own family and invalidate pre-fid access tokens.

    Operational effect: every user's outstanding ACCESS tokens become stale
    (security_version bump). Refresh tokens stay valid and rotate normally.
    """
    # 1. jti is unique per session and fits String(64) -> unique family per legacy row
    op.execute(sa.text(
        "UPDATE refresh_sessions SET family_id = refresh_token_jti "
        "WHERE family_id = 'legacy'"
    ))
    # 2. Invalidate access tokens minted before family isolation existed
    op.execute(sa.text("UPDATE users SET security_version = security_version + 1"))
    # 3. Drop the shared constant default so it can never be reused
    with op.batch_alter_table('refresh_sessions', schema=None) as batch_op:
        batch_op.alter_column(
            'family_id',
            existing_type=sa.String(length=64),
            existing_nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    """Restore the server default only; data backfill and version bump are irreversible by design."""
    with op.batch_alter_table('refresh_sessions', schema=None) as batch_op:
        batch_op.alter_column(
            'family_id',
            existing_type=sa.String(length=64),
            existing_nullable=False,
            server_default='legacy',
        )

