"""Alembic migration: trading goals on risk_settings.

Revision ID: 002_goals
Revises: 001_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002_goals"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "risk_settings",
        sa.Column("weekly_pnl_goal", sa.Numeric(18, 8), nullable=False, server_default="50"),
    )
    op.add_column(
        "risk_settings",
        sa.Column("monthly_pnl_goal", sa.Numeric(18, 8), nullable=False, server_default="200"),
    )
    op.add_column(
        "risk_settings",
        sa.Column("win_rate_goal", sa.Numeric(8, 4), nullable=False, server_default="50"),
    )
    op.add_column(
        "risk_settings",
        sa.Column("followed_plan_goal", sa.Numeric(8, 4), nullable=False, server_default="80"),
    )


def downgrade() -> None:
    op.drop_column("risk_settings", "followed_plan_goal")
    op.drop_column("risk_settings", "win_rate_goal")
    op.drop_column("risk_settings", "monthly_pnl_goal")
    op.drop_column("risk_settings", "weekly_pnl_goal")
