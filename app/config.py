"""Application configuration loaded from environment variables."""

from __future__ import annotations

import logging
import warnings
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Runtime settings for TradeEdge Journal."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TradeEdge Journal"
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = True
    secret_key: str = "dev-only-change-me-in-production"
    admin_username: str = "ahsan"
    admin_password_hash: str = ""
    database_url: str = ""
    default_timezone: str = "Asia/Karachi"
    session_https_only: bool = False
    seed_demo_data: bool = False
    profile_name: str = "Ahsan Trader"
    app_subtitle: str = "Track. Analyze. Improve."

    # MetaTrader 5 (local Exness terminal)
    mt5_enabled: bool = False
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    mt5_terminal_path: str = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
    mt5_symbol_xau: str = "XAUUSDm"
    mt5_symbol_btc: str = "BTCUSDm"
    mt5_history_days: int = 150
    mt5_auto_sync: bool = True
    mt5_auto_sync_minutes: int = 5

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def mt5_symbol_map(self) -> dict[str, str]:
        """MT5 symbol → dashboard market label."""
        return {
            self.mt5_symbol_xau.upper(): "XAU/USD",
            self.mt5_symbol_btc.upper(): "BTC/USD",
        }

    @property
    def using_sqlite(self) -> bool:
        return not bool(self.database_url.strip())

    def resolved_database_url(self) -> str:
        """Return a SQLAlchemy-compatible database URL."""
        raw = self.database_url.strip()
        if not raw:
            warnings.warn(
                "DATABASE_URL is not set — using SQLite fallback for local development only. "
                "Do not use SQLite in production.",
                UserWarning,
                stacklevel=2,
            )
            logger.warning(
                "DATABASE_URL missing; falling back to local SQLite (tradeedge.db)."
            )
            return "sqlite:///./tradeedge.db"

        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg://" + raw[len("postgres://") :]
        elif raw.startswith("postgresql://") and "+psycopg" not in raw:
            raw = "postgresql+psycopg://" + raw[len("postgresql://") :]
        return raw


@lru_cache
def get_settings() -> Settings:
    return Settings()
