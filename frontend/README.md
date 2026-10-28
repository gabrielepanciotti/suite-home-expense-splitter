# HomeExpenseSplitter — Frontend (dashboard web)

Dashboard React (Vite + Tailwind + TypeScript) per la divisione spese member A/member B.
Legge l'API FastAPI `home_expense_splitter_backend` (lettura + scrittura transazioni, riepilogo, grafici, export Excel).

## Stack

- React 18 + TypeScript, **Vite** (dev server porta **3343**)
- **Tailwind CSS** (solo Tailwind, niente CSS ad-hoc) — controlli custom (dropdown, toggle, modale), niente elementi nativi
- **recharts** per i grafici (torta categorie, barre condivise/personali per mese)
- Client API tipizzato in `src/lib/api.ts` (allineato a `home_expense_splitter_backend/schemas.py`, importi in centesimi)

## Sviluppo

Servono **due processi**: backend + frontend.

### 1. Backend API (porta 10009) — dalla root del progetto, con il venv

```bash
# Windows
.venv/Scripts/python.exe -m uvicorn home_expense_splitter_backend.app:app --port 10009 --reload
```

Il backend richiede il DB Postgres `homeexpensesplitter` (container `personal_db`) e `HOMEEXPENSESPLITTER_DATABASE_URL` nel `.env` di root.

### 2. Frontend (porta 3343) — dentro `frontend/`

```bash
cd frontend
npm install      # solo la prima volta
npm run dev      # http://localhost:3343
```

L'URL dell'API è in `frontend/.env`:

```
VITE_API_URL=http://localhost:10009
```

> CORS: il backend è già configurato per accettare `http://localhost:3343`.

## Build di produzione

```bash
cd frontend
npm run build    # type-check (tsc -b) + bundle Vite in dist/
npm run preview  # anteprima del build
```

## Struttura

```
frontend/
  src/
    App.tsx     shell (AppShell + VistaProvider): navigazione dalle sezioni di useVista, sezioni via hash
    pages/      Saldo, Spese, Esporta (una per sezione della vista: saldo, spese, esporta)
    components/ SaldoHeader, RiepilogoPanel, SpeseCondivisePanel (+ Elenco mobile), dialog di saldo e rimborso,
                ExportButton, icone SVG inline
    hooks/      useSummary, useSharedExpenses, useCompactViewport
    lib/        api.ts (client tipizzato), format.ts (euro/date it-IT), errors.ts (errori in italiano)
    i18n/       it.ts, en.ts (chiavi vista.*, errors.*, ...)
```

## Note

- Tutti gli importi sono **centesimi interi** lato API; in UI si mostrano in € con formattazione `it-IT`.
- Dopo ogni mutazione (add/edit/delete) la tabella e le viste derivate (saldo, grafici, riepilogo) si aggiornano.
- Il saldo mostrato sul dataset reale deve essere **€ 4.767,94**.
