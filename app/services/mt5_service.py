"""
MetaTrader 5 sync for Exness (local terminal only).

Pulls closed deals for configured symbols, upserts into the trades table.
Older trades already stored in the DB are never deleted — stats keep using
the full history. The MT5 lookback window only controls how far back each
sync reads from the terminal (default 30 days) to catch new closes.
"""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.trade import Trade, TradeStatus
from app.repositories.trade_repository import TradeRepository
from app.utils.dates import ensure_aware, parse_datetime
from app.utils.decimals import ZERO, money

logger = logging.getLogger(__name__)

SOURCE = "MT5"
EXPORT_CSV = Path(__file__).resolve().parents[2] / "data" / "mt5_live" / "deals.csv"


@dataclass
class SyncResult:
    connected: bool = False
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    closed_found: int = 0
    errors: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "imported": self.imported,
            "updated": self.updated,
            "skipped": self.skipped,
            "closed_found": self.closed_found,
            "errors": self.errors,
            "message": self.message,
        }


def _try_import_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore

        return mt5
    except ImportError:
        return None


def map_market(symbol: str, settings: Settings) -> str | None:
    return settings.mt5_symbol_map.get(symbol.upper())


def _deal_time(deal) -> datetime:
    """Convert MT5 deal time (UTC epoch seconds) to aware UTC datetime."""
    return datetime.fromtimestamp(int(deal.time), tz=timezone.utc)


def _direction_from_deals(entry_deal, exit_deal) -> str:
    # DEAL_TYPE_BUY = 0, DEAL_TYPE_SELL = 1
    # Position direction is the entry deal type
    dtype = int(getattr(entry_deal, "type", 0))
    return "BUY" if dtype == 0 else "SELL"


def _status_from_profit(net: Decimal) -> str:
    if net > ZERO:
        return TradeStatus.WIN.value
    if net < ZERO:
        return TradeStatus.LOSS.value
    return TradeStatus.BREAKEVEN.value


def _fetch_sl_tp(mt5, position_id: int) -> tuple[Decimal | None, Decimal | None]:
    orders = mt5.history_orders_get(position=position_id)
    if not orders:
        return None, None
    # Prefer the last order that still has SL/TP set
    sl = tp = None
    for order in orders:
        if getattr(order, "sl", 0):
            sl = Decimal(str(order.sl))
        if getattr(order, "tp", 0):
            tp = Decimal(str(order.tp))
    return sl, tp


def build_closed_trades_from_deals(
    deals: list,
    settings: Settings,
    mt5=None,
) -> list[dict[str, Any]]:
    """Group MT5 deals by position_id into closed trade payloads."""
    by_position: dict[int, list] = defaultdict(list)
    for deal in deals:
        symbol = str(getattr(deal, "symbol", "") or "")
        if map_market(symbol, settings) is None:
            continue
        # Ignore balance/credit operations (type 2+)
        if int(getattr(deal, "type", 0)) not in (0, 1):
            continue
        pos_id = int(getattr(deal, "position_id", 0) or 0)
        if pos_id <= 0:
            continue
        by_position[pos_id].append(deal)

    rows: list[dict[str, Any]] = []
    for pos_id, pos_deals in by_position.items():
        pos_deals = sorted(pos_deals, key=lambda d: (d.time, d.ticket))
        entries = [d for d in pos_deals if int(getattr(d, "entry", -1)) == 0]  # DEAL_ENTRY_IN
        exits = [d for d in pos_deals if int(getattr(d, "entry", -1)) in (1, 3)]  # OUT / OUT_BY
        if not entries or not exits:
            # Some brokers mark differently — fallback: first/last deal
            if len(pos_deals) < 2:
                continue
            entries = [pos_deals[0]]
            exits = [pos_deals[-1]]
            if entries[0].ticket == exits[0].ticket:
                continue

        entry_deal = entries[0]
        exit_deal = exits[-1]
        symbol = str(entry_deal.symbol)
        market = map_market(symbol, settings)
        if not market:
            continue

        direction = _direction_from_deals(entry_deal, exit_deal)
        entry_price = Decimal(str(entry_deal.price))
        exit_price = Decimal(str(exit_deal.price))
        volume = Decimal(str(exit_deal.volume or entry_deal.volume or 0))
        if volume <= ZERO:
            continue

        # Aggregate money fields across all deals in the position
        profit = sum((Decimal(str(getattr(d, "profit", 0) or 0)) for d in pos_deals), ZERO)
        commission = sum((Decimal(str(getattr(d, "commission", 0) or 0)) for d in pos_deals), ZERO)
        swap = sum((Decimal(str(getattr(d, "swap", 0) or 0)) for d in pos_deals), ZERO)
        fee = sum((Decimal(str(getattr(d, "fee", 0) or 0)) for d in pos_deals), ZERO)
        # Commission/swap are usually negative in MT5
        net = money(profit + commission + swap + fee)
        gross = money(profit)

        sl = tp = None
        if mt5 is not None:
            try:
                sl, tp = _fetch_sl_tp(mt5, pos_id)
            except Exception:  # noqa: BLE001
                sl = tp = None

        open_dt = ensure_aware(_deal_time(entry_deal), settings.default_timezone)
        close_dt = ensure_aware(_deal_time(exit_deal), settings.default_timezone)

        # Rough pip/point distance (display only)
        pips = money(abs(exit_price - entry_price), 5)

        rows.append(
            {
                "external_ticket": str(pos_id),
                "trade_date": open_dt,
                "close_date": close_dt,
                "market": market,
                "direction": direction,
                "status": _status_from_profit(net),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "lot_size": volume,
                "stop_loss": sl,
                "take_profit": tp,
                "profit_loss": gross,
                "commission": abs(commission),
                "swap": abs(swap) if swap != ZERO else ZERO,
                # Keep sign of commission in net already; store absolute costs for display
                "fees": abs(fee),
                "net_profit_loss": net,
                "pips": pips,
                "source": SOURCE,
                "entry_reason": f"Synced from MT5 ({symbol})",
                "exit_reason": (getattr(exit_deal, "comment", None) or None),
            }
        )
    return rows


def connect_mt5(settings: Settings | None = None):
    """Initialize and log into the local MT5 terminal. Returns (mt5_module, error)."""
    settings = settings or get_settings()
    mt5 = _try_import_mt5()
    if mt5 is None:
        return None, "MetaTrader5 package is not installed. Run: pip install MetaTrader5"
    if not settings.mt5_enabled:
        return None, "MT5 sync is disabled (MT5_ENABLED=false)."
    if not settings.mt5_login or not settings.mt5_password or not settings.mt5_server:
        return None, "MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER must be set in .env."

    path = settings.mt5_terminal_path.strip() or None
    login = int(settings.mt5_login)
    password = settings.mt5_password
    server = settings.mt5_server.strip()

    # Preferred: initialize with credentials in one step (Exness-friendly)
    init_kwargs: dict[str, Any] = {
        "login": login,
        "password": password,
        "server": server,
    }
    if path:
        init_kwargs["path"] = path

    ok = mt5.initialize(**init_kwargs)
    if not ok:
        # Fallback: attach to an already-open terminal, then login
        ok = mt5.initialize(path=path) if path else mt5.initialize()
        if not ok:
            err = mt5.last_error()
            return (
                None,
                f"MT5 initialize failed: {err}. Open the Exness MT5 terminal once, then retry.",
            )
        info = mt5.account_info()
        if info is not None and int(info.login) == login:
            return mt5, None
        authorized = mt5.login(login=login, password=password, server=server)
        if not authorized:
            err = mt5.last_error()
            mt5.shutdown()
            return (
                None,
                f"MT5 login failed: {err}. "
                "Open Exness MT5, log in manually with this account, enable Algo Trading, then sync again. "
                "Confirm server is exactly Exness-MT5Real35 and the password is correct.",
            )
        return mt5, None

    info = mt5.account_info()
    if info is None:
        err = mt5.last_error()
        mt5.shutdown()
        return None, f"MT5 connected but account_info failed: {err}"
    return mt5, None


def _upsert_rows(db: Session, rows: list[dict[str, Any]], result: SyncResult) -> None:
    repo = TradeRepository(db)
    result.closed_found = len(rows)
    for row in rows:
        existing = db.scalar(
            select(Trade).where(
                Trade.source == SOURCE,
                Trade.external_ticket == row["external_ticket"],
            )
        )
        if existing is None:
            existing = repo.find_duplicate(
                row["external_ticket"],
                row["trade_date"],
                row["market"],
            )

        if existing:
            for key in (
                "trade_date",
                "close_date",
                "direction",
                "status",
                "entry_price",
                "exit_price",
                "lot_size",
                "stop_loss",
                "take_profit",
                "profit_loss",
                "commission",
                "swap",
                "fees",
                "net_profit_loss",
                "pips",
            ):
                if key in row:
                    setattr(existing, key, row[key])
            existing.source = SOURCE
            repo.update(existing)
            result.updated += 1
        else:
            trade = Trade(**{k: v for k, v in row.items() if hasattr(Trade, k)})
            repo.add(trade)
            result.imported += 1


def _rows_from_export_csv(settings: Settings, path: Path | None = None) -> list[dict[str, Any]]:
    """Build closed-trade rows from EA-exported deals.csv."""
    csv_path = path or EXPORT_CSV
    if not csv_path.exists():
        return []

    deals_raw: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            symbol = (row.get("symbol") or "").strip()
            if map_market(symbol, settings) is None:
                continue
            try:
                dtype = int(float(row.get("type") or 0))
            except ValueError:
                continue
            if dtype not in (0, 1):
                continue
            pos_id = int(float(row.get("position_id") or 0))
            if pos_id <= 0:
                continue
            t = parse_datetime(row.get("time"), settings.default_timezone)
            if t is None:
                continue
            deals_raw.append(
                {
                    "position_id": pos_id,
                    "ticket": int(float(row.get("ticket") or 0)),
                    "symbol": symbol,
                    "entry": int(float(row.get("entry") or 0)),
                    "type": dtype,
                    "volume": Decimal(str(row.get("volume") or 0)),
                    "price": Decimal(str(row.get("price") or 0)),
                    "profit": Decimal(str(row.get("profit") or 0)),
                    "commission": Decimal(str(row.get("commission") or 0)),
                    "swap": Decimal(str(row.get("swap") or 0)),
                    "fee": Decimal(str(row.get("fee") or 0)),
                    "time": t,
                    "comment": row.get("comment") or "",
                    "sl": Decimal(str(row.get("sl") or 0)) or None,
                    "tp": Decimal(str(row.get("tp") or 0)) or None,
                }
            )

    by_position: dict[int, list] = defaultdict(list)
    for d in deals_raw:
        by_position[d["position_id"]].append(d)

    rows: list[dict[str, Any]] = []
    for pos_id, pos_deals in by_position.items():
        pos_deals = sorted(pos_deals, key=lambda x: (x["time"], x["ticket"]))
        entries = [d for d in pos_deals if d["entry"] == 0]
        exits = [d for d in pos_deals if d["entry"] in (1, 3)]
        if not entries or not exits:
            if len(pos_deals) < 2:
                continue
            entries, exits = [pos_deals[0]], [pos_deals[-1]]
        entry_d, exit_d = entries[0], exits[-1]
        market = map_market(entry_d["symbol"], settings)
        if not market:
            continue
        volume = exit_d["volume"] or entry_d["volume"]
        if volume <= ZERO:
            continue
        profit = sum((d["profit"] for d in pos_deals), ZERO)
        commission = sum((d["commission"] for d in pos_deals), ZERO)
        swap = sum((d["swap"] for d in pos_deals), ZERO)
        fee = sum((d["fee"] for d in pos_deals), ZERO)
        net = money(profit + commission + swap + fee)
        sl = next((d["sl"] for d in reversed(pos_deals) if d.get("sl")), None)
        tp = next((d["tp"] for d in reversed(pos_deals) if d.get("tp")), None)
        if sl == ZERO:
            sl = None
        if tp == ZERO:
            tp = None
        rows.append(
            {
                "external_ticket": str(pos_id),
                "trade_date": ensure_aware(entry_d["time"], settings.default_timezone),
                "close_date": ensure_aware(exit_d["time"], settings.default_timezone),
                "market": market,
                "direction": "BUY" if entry_d["type"] == 0 else "SELL",
                "status": _status_from_profit(net),
                "entry_price": entry_d["price"],
                "exit_price": exit_d["price"],
                "lot_size": volume,
                "stop_loss": sl,
                "take_profit": tp,
                "profit_loss": money(profit),
                "commission": abs(commission),
                "swap": abs(swap),
                "fees": abs(fee),
                "net_profit_loss": net,
                "pips": money(abs(exit_d["price"] - entry_d["price"]), 5),
                "source": SOURCE,
                "entry_reason": f"Synced from MT5 export ({entry_d['symbol']})",
                "exit_reason": exit_d.get("comment") or None,
            }
        )
    return rows


def sync_from_export_file(db: Session, settings: Settings | None = None) -> SyncResult:
    """Import closed trades from EA CSV export (Exness-safe fallback)."""
    settings = settings or get_settings()
    result = SyncResult(connected=True)
    if not EXPORT_CSV.exists():
        result.connected = False
        result.message = (
            f"No export file at {EXPORT_CSV}. "
            "Run scripts/TradeEdge_ExportDeals.mq5 in Exness MT5, then sync again."
        )
        result.errors.append(result.message)
        return result
    rows = _rows_from_export_csv(settings, EXPORT_CSV)
    _upsert_rows(db, rows, result)
    result.message = (
        f"Imported from MT5 export file: {result.imported} new, {result.updated} updated "
        f"({result.closed_found} closed positions). Older DB trades kept for statistics."
    )
    return result


def sync_closed_trades(db: Session, settings: Settings | None = None) -> SyncResult:
    """
    Sync closed XAU/BTC trades from MT5 into the database.

    Tries the MetaTrader5 Python API first. If Exness blocks API auth (-6),
    falls back to the EA CSV export at data/mt5_live/deals.csv.

    Older trades already in the DB are never deleted.
    """
    settings = settings or get_settings()
    result = SyncResult()
    mt5, err = connect_mt5(settings)
    if err or mt5 is None:
        # Fall back to EA export file
        file_result = sync_from_export_file(db, settings)
        if file_result.closed_found or file_result.imported or file_result.updated:
            file_result.message = (
                f"API unavailable ({err}). Used EA export instead. {file_result.message}"
            )
            return file_result
        result.message = (
            f"{err} "
            "Workaround: in MT5 run Scripts\\\\TradeEdge_ExportDeals.mq5, "
            f"then click Sync again (expects {EXPORT_CSV})."
        )
        result.errors.append(err or "MT5 unavailable")
        return result

    result.connected = True
    try:
        days = max(1, int(settings.mt5_history_days))
        date_to = datetime.now(timezone.utc) + timedelta(hours=1)
        date_from = date_to - timedelta(days=days)
        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None:
            result.errors.append(f"history_deals_get failed: {mt5.last_error()}")
            # Try file fallback
            file_result = sync_from_export_file(db, settings)
            if file_result.closed_found:
                return file_result
            result.message = result.errors[-1]
            return result

        rows = build_closed_trades_from_deals(list(deals), settings, mt5=mt5)
        _upsert_rows(db, rows, result)
        result.message = (
            f"MT5 sync complete: {result.imported} new, {result.updated} updated, "
            f"{result.closed_found} closed positions in last {days} days. "
            "Older stored trades were kept for statistics."
        )

        try:
            info = mt5.account_info()
            if info is not None:
                from decimal import Decimal as D

                from app.repositories.settings_repository import SettingsRepository

                risk = SettingsRepository(db).get_risk_settings()
                risk.current_balance = D(str(info.balance))
                SettingsRepository(db).save_risk_settings(risk)
                result.message += f" Balance updated to {info.balance:.2f} {info.currency}."
        except Exception:  # noqa: BLE001
            pass

        logger.info(result.message)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("MT5 sync failed")
        result.errors.append(str(exc))
        result.message = f"MT5 sync error: {exc}"
        return result
    finally:
        try:
            mt5.shutdown()
        except Exception:  # noqa: BLE001
            pass


def mt5_account_info(settings: Settings | None = None) -> dict[str, Any]:
    """Return basic account info for UI status, or an error payload."""
    settings = settings or get_settings()
    mt5, err = connect_mt5(settings)
    if err or mt5 is None:
        export_exists = EXPORT_CSV.exists()
        return {
            "ok": False,
            "error": err,
            "export_file_ready": export_exists,
            "export_path": str(EXPORT_CSV),
        }
    try:
        info = mt5.account_info()
        if info is None:
            return {"ok": False, "error": str(mt5.last_error())}
        return {
            "ok": True,
            "login": info.login,
            "server": info.server,
            "name": info.name,
            "balance": float(info.balance),
            "equity": float(info.equity),
            "currency": info.currency,
            "company": info.company,
        }
    finally:
        mt5.shutdown()
