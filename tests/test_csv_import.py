"""CSV import validation tests."""

from app.services import csv_service

SAMPLE = """trade_date,close_date,market,direction,status,entry_price,exit_price,lot_size,profit_loss,commission,swap,fees,net_profit_loss,external_ticket
2026-01-10T10:30:00,2026-01-10T14:00:00,XAU/USD,BUY,WIN,2650,2660,0.1,100,2,0,0,98,DUP-1
2026-01-11T10:30:00,2026-01-11T14:00:00,BTC/USD,SELL,LOSS,90000,91000,0.05,-50,2,0,0,-52,OK-2
bad-date,,XAU/USD,BUY,WIN,0,2660,0.1,100,0,0,0,100,BAD-3
"""


def test_csv_validation():
    fmt, rows = csv_service.parse_csv_content(SAMPLE)
    assert fmt in ("standard", "unknown") or fmt == "standard"
    preview = csv_service.validate_import_rows(rows, "standard")
    assert preview["total"] == 3
    assert preview["valid_count"] >= 1
    assert preview["invalid_count"] >= 1


def test_duplicate_detection():
    fmt, rows = csv_service.parse_csv_content(SAMPLE)
    existing = {("DUP-1", "XAU/USD", "2026-01-10")}
    preview = csv_service.validate_import_rows(rows, "standard", existing_tickets=existing)
    assert preview["duplicate_count"] >= 1


def test_mt5_detection():
    mt5 = """Ticket,Open Time,Type,Symbol,Volume,Open Price,Close Time,Close Price,Profit
1,2026-02-01 11:00:00,buy,XAUUSD,0.1,2650,2026-02-01 12:00:00,2660,100
"""
    fmt, rows = csv_service.parse_csv_content(mt5)
    assert fmt == "mt5"
    preview = csv_service.validate_import_rows(rows, fmt)
    assert preview["valid_count"] >= 1


def test_export_roundtrip_fields():
    csv_text = csv_service.sample_template_csv()
    assert "market" in csv_text
    assert "entry_price" in csv_text
