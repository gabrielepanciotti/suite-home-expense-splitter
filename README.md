# HomeExpenseSplitter

HomeExpenseSplitter calculates a transparent settlement for a shared household: it reads confirmed shared expenses from a finance service, applies configurable split rules or an explicit per-expense share, tracks settlements and reimbursements, and produces a final Excel summary. It deliberately does not create or modify ledger expenses.

## Features

- Exact integer-cent calculations with deterministic rounding.
- Configurable percentages and excluded categories, with per-expense overrides.
- FastAPI API, React interface, CLI, Excel export, and optional read-only Telegram bot.
- Settlement, reimbursement, and view-preference state stored separately from the expense ledger.

## Requirements

- Python 3.13 and Node.js 20.
- The Life framework checked out as a sibling directory named `Life`; it provides `suite_core`, `suite_backend_core`, and the frontend design packages.
- A PostgreSQL database for normal operation (the test suite uses local SQLite and mocked finance HTTP responses).

## Quickstart

```bash
git clone <your-fork-url> home-expense-splitter
git clone <life-framework-url> Life
cd home-expense-splitter
cp .env.example .env
python3.13 -m venv .venv
.venv/bin/pip install ../Life/packages/shared ../Life/packages/backend-core -r backend/requirements.txt
cd frontend && npm ci && cd ..
```

Set the database and finance-service values in `.env`, then start the API and frontend in separate terminals:

```bash
PYTHONPATH=backend .venv/bin/python -m uvicorn home_expense_splitter_backend.app:app --port 10009
cd frontend && npm run dev
```

For Docker, copy `deploy/docker-compose.example.yml`, run `bash deploy/prebuild.sh` to vendor the sibling framework packages, then run `docker compose --env-file .env -f deploy/docker-compose.example.yml up --build`. The production compose files are intentionally not part of the public release.

## Tests

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
cd frontend && npm test -- --pool=forks --poolOptions.forks.maxForks=2 --poolOptions.forks.minForks=1 && npm run build
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Primary database connection URL. |
| `HOMEEXPENSESPLITTER_DATABASE_URL` | Application-specific database connection URL. |
| `DB_PASSWORD` | Password used by the example Docker database. |
| `DB_HOST_PORT` | Host port for the example Docker database. |
| `FINANCE_URL` | Base URL of the service that owns confirmed expenses. |
| `HOMEEXPENSESPLITTER_SPLIT_SOURCE` | Expense source (`finance` or `ledger`). |
| `MEMBER_ALIASES_JSON` | Optional local display names for the two members. |
| `HOMEEXPENSESPLITTER_TELEGRAM_TOKEN` | Optional Telegram bot token. |
| `CORS_ORIGINS` | Allowed browser origins. |
| `LIFE_GATE_JWKS_URL` | Optional Life access-gate JWKS endpoint. |
| `LIFE_INSTANCE` | Optional Life instance identifier. |
| `LIFE_VISTA_DEFAULT_ROLE` | Default role when no access gate is configured. |

The current root README is English; the prior Italian introduction is available as [README.it.md](README.it.md). See [docs/guida.md](docs/guida.md) for the Italian user guide.

## License

MIT — see [LICENSE](LICENSE).
