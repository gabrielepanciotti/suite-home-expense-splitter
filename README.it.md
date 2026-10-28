# HomeExpenseSplitter

Il **divisore** delle spese di casa, nodo della rete Life: legge dal nodo `finance` le uscite
condivise confermate, applica la regola di casa (`backend/config/split_config.toml`) o la quota
esplicita della riga, tiene settlements e rimborsi con il member B e produce il Riepilogo Finale.
Non registra uscite: quelle stanno in `finance`, la cattura in `expenseTracker`.

## Setup (Windows, Python 3.13)

```bash
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

Il nodo `finance` deve rispondere su `FINANCE_URL` (default `http://127.0.0.1:10023`).

## Uso

Guida d'uso: [`docs/guida.md`](docs/guida.md).

```powershell
$env:PYTHONPATH="backend"
.venv/Scripts/python.exe -m home_expense_splitter.cli split
.venv/Scripts/python.exe -m home_expense_splitter.cli split --save
.venv/Scripts/python.exe -m home_expense_splitter.cli export-excel
.venv/Scripts/python.exe -m home_expense_splitter.cli rimborso <raw_hash>
```

## Test

```bash
.venv/Scripts/python.exe -m pytest -q
```
