"""add booking source

Revision ID: a3c91d7e5b42
Revises: fe8b60b1cce6
Create Date: 2026-11-12 09:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c91d7e5b42'
down_revision: str | None = 'fe8b60b1cce6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default để các booking đã có trong DB được gán 'staff', cột không bị NULL
    op.add_column('bookings', sa.Column(
        'source', sa.String(length=20), nullable=False, server_default='staff'))


def downgrade() -> None:
    op.drop_column('bookings', 'source')
