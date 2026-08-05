"""Initial schema for TradeEdge Journal.

Revision ID: 001_initial
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("market", sa.String(16), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("lot_size", sa.Numeric(18, 8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(18, 8), nullable=True),
        sa.Column("profit_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("commission", sa.Numeric(18, 8), nullable=False),
        sa.Column("swap", sa.Numeric(18, 8), nullable=False),
        sa.Column("fees", sa.Numeric(18, 8), nullable=False),
        sa.Column("net_profit_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("pips", sa.Numeric(18, 8), nullable=True),
        sa.Column("risk_amount", sa.Numeric(18, 8), nullable=True),
        sa.Column("planned_reward", sa.Numeric(18, 8), nullable=True),
        sa.Column("risk_reward_ratio", sa.Numeric(12, 4), nullable=True),
        sa.Column("realized_r_multiple", sa.Numeric(12, 4), nullable=True),
        sa.Column("account_balance_after", sa.Numeric(18, 8), nullable=True),
        sa.Column("setup", sa.String(64), nullable=True),
        sa.Column("timeframe", sa.String(8), nullable=True),
        sa.Column("trading_session", sa.String(64), nullable=True),
        sa.Column("entry_reason", sa.Text(), nullable=True),
        sa.Column("exit_reason", sa.Text(), nullable=True),
        sa.Column("mistake", sa.Text(), nullable=True),
        sa.Column("lesson", sa.Text(), nullable=True),
        sa.Column("emotion_before", sa.String(64), nullable=True),
        sa.Column("emotion_after", sa.String(64), nullable=True),
        sa.Column("followed_plan", sa.Boolean(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("screenshot_url", sa.String(512), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("external_ticket", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trades_trade_date", "trades", ["trade_date"])
    op.create_index("ix_trades_market", "trades", ["market"])
    op.create_index("ix_trades_status", "trades", ["status"])
    op.create_index("ix_trades_setup", "trades", ["setup"])
    op.create_index("ix_trades_external_ticket", "trades", ["external_ticket"])
    op.create_index("ix_trades_source", "trades", ["source"])

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trade_id", sa.Integer(), sa.ForeignKey("trades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("market", sa.String(16), nullable=True),
        sa.Column("setup", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("lesson", sa.Text(), nullable=True),
        sa.Column("mistakes", sa.Text(), nullable=True),
        sa.Column("emotional_state", sa.String(64), nullable=True),
        sa.Column("followed_plan", sa.Boolean(), nullable=True),
        sa.Column("tags", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_journal_entries_entry_date", "journal_entries", ["entry_date"])
    op.create_index("ix_journal_entries_trade_id", "journal_entries", ["trade_id"])

    op.create_table(
        "risk_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("starting_balance", sa.Numeric(18, 8), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 8), nullable=False),
        sa.Column("default_risk_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("maximum_risk_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("daily_loss_limit_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("weekly_loss_limit_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("maximum_trades_per_day", sa.Integer(), nullable=False),
        sa.Column("maximum_consecutive_losses", sa.Integer(), nullable=False),
        sa.Column("maximum_total_open_risk_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("base_currency", sa.String(8), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("default_dashboard_period", sa.String(32), nullable=False),
        sa.Column("default_market_filter", sa.String(16), nullable=False),
        sa.Column("number_format", sa.String(32), nullable=False),
        sa.Column("date_format", sa.String(32), nullable=False),
        sa.Column("table_density", sa.String(16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "symbol_configurations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market", sa.String(16), nullable=False),
        sa.Column("contract_size", sa.Numeric(18, 8), nullable=False),
        sa.Column("tick_size", sa.Numeric(18, 8), nullable=False),
        sa.Column("tick_value_per_lot", sa.Numeric(18, 8), nullable=False),
        sa.Column("pip_size", sa.Numeric(18, 8), nullable=False),
        sa.Column("decimal_places", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("market", name="uq_symbol_market"),
    )


def downgrade() -> None:
    op.drop_table("symbol_configurations")
    op.drop_table("risk_settings")
    op.drop_table("journal_entries")
    op.drop_table("trades")
