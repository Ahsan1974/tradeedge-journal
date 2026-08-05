# TradeEdge Journal

Personal trading journal and analytics dashboard for **XAU/USD** and **BTC/USD**.

**Track. Analyze. Improve.**

Built for a single trader (**Ahsan Trader**) — not a multi-tenant SaaS product. No subscriptions, teams, or billing.

## Features

- Record, edit, and delete XAU/USD & BTC/USD trades
- Dashboard KPIs, Chart.js visuals, market comparison
- Journal with lessons, emotions, and plan-followed tracking
- Analytics by setup, session, timeframe, direction, and time
- Position-size and risk-to-reward calculators
- Daily risk monitor and discipline score (informational)
- Monthly P/L calendar heatmap
- CSV import (TradeEdge template + basic MT5 history) with preview
- CSV export (all / filtered / market / month)
- Personal single-user journal (no login required)
- SQLite locally, PostgreSQL (Neon) on Vercel

## Technology stack

| Layer | Stack |
|--------|--------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic, Jinja2 |
| Auth | None (personal local/private use); session cookie for CSRF + flash messages only |
| DB | PostgreSQL (psycopg) in production, SQLite locally |
| Frontend | Server-rendered HTML, custom CSS, vanilla JS, Chart.js, Lucide |
| Deploy | Vercel serverless Python + external Postgres |

## Folder structure

```
app.py                 # FastAPI entry (Vercel + local)
app/                   # Application package (models, routers, services, templates)
public/                # Static CSS/JS/images
migrations/            # Alembic migrations
scripts/               # Password hash, DB init, demo seed
data/                  # Sample CSV files
tests/                 # Pytest suite
requirements.txt
vercel.json
.env.example
```

## Local setup

### 1. Create virtual environment

**Windows PowerShell**

```powershell
cd "D:\Trading Dashboard"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux**

```bash
cd "Trading Dashboard"
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

Edit `.env` and set at least `SECRET_KEY`.

Leave `DATABASE_URL` empty for local SQLite (`tradeedge.db`).

Authentication is disabled — the dashboard opens directly with no login.

```powershell
python scripts/initialize_database.py
```

Or with Alembic (PostgreSQL / production-style):

```powershell
alembic upgrade head
python scripts/initialize_database.py
```

### 3. Initialize database

```powershell
python scripts/seed_demo_data.py
```

Remove demo rows only:

```powershell
python scripts/seed_demo_data.py --clear-demo
```

Demo trades use `source="DEMO"` so they can be deleted safely.

### 6. Run locally

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

(`app:app` loads the `app` package, which exports the FastAPI instance from `app.main`.)

Alternatively:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and sign in.

## Tests

```powershell
pytest -q
```

Tests use an isolated temporary SQLite database and do **not** require Neon.

## Lint

```powershell
ruff check .
```

## CSV import format

### TradeEdge template

Download from **Trades → Import → Download template**, or use `data/sample_trades.csv`.

Required ideas: `trade_date`, `market` (`XAU/USD` or `BTC/USD`), `direction`, `status`, `entry_price`, `lot_size`. Closed trades need exit/P&L fields.

### MT5-style history

See `data/sample_mt5_history.csv`. Common aliases (`Ticket`, `Symbol`, `Profit`, etc.) are mapped automatically.

Import always **previews first**; nothing is written until you confirm.

## Neon PostgreSQL setup

1. Create a Neon project and copy the connection string.
2. Set `DATABASE_URL` (either `postgres://` or `postgresql://` — both are normalized to `postgresql+psycopg://`).
3. Run migrations:

```powershell
alembic upgrade head
python scripts/initialize_database.py
```

Do **not** use SQLite on Vercel.

## Vercel deployment

1. Push this repository to GitHub.
2. Import the project in Vercel (Python runtime).
3. Set environment variables (below).
4. Attach Neon (or another hosted Postgres) via `DATABASE_URL`.
5. Deploy. Root `app.py` exposes `app = FastAPI(...)`.
6. Static assets are served from `/public`.

### Required Vercel environment variables

| Variable | Notes |
|----------|--------|
| `SECRET_KEY` | Long random string |
| `ADMIN_USERNAME` | Your login name |
| `ADMIN_PASSWORD_HASH` | bcrypt hash from the script |
| `DATABASE_URL` | Neon/Postgres URL |
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `SESSION_HTTPS_ONLY` | `true` |
| `DEFAULT_TIMEZONE` | `Asia/Karachi` (or your preference) |
| `SEED_DEMO_DATA` | `false` |

Optional: `APP_NAME=TradeEdge Journal`

## Broker-specific symbol settings

Tick size, tick value, pip size, and contract size **differ by broker**. Defaults in Settings are examples only. Update **XAU/USD** and **BTC/USD** configuration to match your broker before trusting position-size estimates. Stored `net_profit_loss` remains the authoritative result.

## Security limitations (personal use)

- Single shared login via environment variables — not multi-user IAM
- No password reset / registration
- Session cookie auth is appropriate for a private journal, not a public SaaS
- Keep `.env` and password hashes out of git
- CSRF protects mutating forms; still use HTTPS in production

## Backup

Use **Trades → Export** (all / market / month / filtered) regularly and store the CSV offline.

## Troubleshooting

| Issue | Fix |
|--------|-----|
| Login always fails | Regenerate `ADMIN_PASSWORD_HASH`; ensure no extra quotes in `.env` |
| SQLite warning on startup | Expected locally when `DATABASE_URL` is empty |
| Charts empty | Seed demo data or add closed trades; check filters |
| Vercel DB errors | Confirm `DATABASE_URL`, SSL, and `alembic upgrade head` |
| CSRF 403 | Refresh the page and resubmit the form |
| Import cookie too large | Import fewer rows at a time (preview capped) |

## Reasonable limitations

- No live broker API, signals, or auto-trading
- No WebSockets / background workers
- Import preview is stored in the signed session (size-limited)
- Risk score and calculators are informational, not financial advice
- P/L formulas are broker-dependent; prefer recording broker P/L

## License

Personal use. Adjust freely for your own journal.
