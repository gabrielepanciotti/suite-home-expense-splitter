# Guida d'uso — HomeExpenseSplitter

Per chi usa l'app. Per chi sviluppa: `CLAUDE.md` e `.claude/docs/`.

## Cosa fa
Divide le spese di casa condivise fra il member A e il member B e dice quanto il member B deve al
member A.
- Le uscite **non si registrano qui**: si inseriscono nel nodo **finance** o si importano con
  **ExpenseTracker**. Questa app legge da finance le uscite condivise confermate.
- Applica la **regola di casa** di `backend/config/split_config.toml` (percentuali e categorie escluse).
  Se una riga in finance ha una quota esplicita (`member_b_share_bp`), vale quella.
- Mostra il saldo e il **Riepilogo divisione** per categoria, ed esporta il Riepilogo Finale in Excel.

## Come si apre
Nessun login: finché l'istanza non ha il cancello di accesso Life, chiunque apre l'app è
**Proprietario** e vede tutto.

| dove | interfaccia | API |
|---|---|---|
| dev, PC personale | http://127.0.0.1:3343 (indice dei nodi: http://srv.localhost:7777) | http://127.0.0.1:10009 |
| prod istanza personal (oggi replica su dev-linux) | http://127.0.0.1:3343 su quella macchina, via Tailscale o tunnel ssh | http://127.0.0.1:10009 |

## Il menu e i ruoli
Il menu a lato ha tre sezioni: **Saldo** (saldo e «Riepilogo divisione»), **Spese condivise** (elenco
con lo stato dei rimborsi) ed **Esporta** (Excel del Riepilogo Finale). Il menu mostra solo le sezioni
che il tuo ruolo può vedere; i pulsanti che il ruolo non consente non compaiono.

| ruolo | vede | può fare |
|---|---|---|
| Ospite | Saldo, Spese condivise | solo guardare |
| Membro | anche Esporta | «Salva saldo», «Segna rimborsata», «Annulla rimborso», «Scarica Excel» |
| Proprietario | tutto | come il Membro |

Se un'azione viene rifiutata compare «Non hai il permesso per questa azione: serve il ruolo Membro.»

## Personalizza vista
Il pulsante «Personalizza vista» apre un pannello con le sezioni che puoi vedere. Per ognuna:
- l'interruttore la **mostra o nasconde** nel menu;
- le frecce la **spostano su o giù**;
- la stella la mette nei **preferiti**: le preferite salgono in cima al menu.

Le scelte si salvano subito, per persona, e valgono su ogni dispositivo. «Ripristina» torna
all'ordine di partenza.

## Tema chiaro e scuro
L'app segue il tema del sistema operativo o del browser: chiaro di giorno, scuro se il sistema è
in modalità scura. Nell'app non c'è un comando per cambiarlo.

## Casi d'uso
1. **Quanto deve il member B.** Sezione «Saldo»: nel riquadro «Saldo divisione spese», c'è
   «member B deve a member A» con «Totale divisibile», «Quota» e «Bonifici netti».
2. **Riepilogo per categoria.** Sempre in «Saldo», sotto il saldo, la tabella «Riepilogo divisione» (Categoria, Importo).
3. **Riepilogo in Excel.** Sezione «Esporta» (per ruolo Membro o superiore), pulsante «Scarica Excel»:
   scarica il solo foglio Riepilogo Finale. I dettagli delle uscite si esportano da finance.
4. **Registrare un saldo dopo un pagamento.** Nel riquadro del saldo premi «Salva saldo» (ruolo Membro): si apre
   «Salva il saldo» con l'importo corrente (non modificabile), la «Data» (di default oggi) e una «Nota
   facoltativa». Premi «Conferma e salva»: compare «Saldo salvato correttamente.» e il riquadro si
   aggiorna. In alternativa, da riga di comando:
   ```bash
   PYTHONPATH=backend .venv/bin/python -m home_expense_splitter.cli split --save --date 2026-10-25 --note "bonifico ottobre"
   ```
   Su Windows: `./menu.ps1 split`.
5. **Una spesa condivisa già rimborsata dal member B** (esce dalla divisione). Nella sezione «Spese
   condivise» (ruolo Membro) premi «Segna rimborsata» sulla riga della spesa: scegli la «Data del rimborso»
   (obbligatoria), aggiungi se vuoi una nota e premi «Conferma rimborso». La riga passa a «Rimborsata»
   con la data e il saldo si ricalcola. Per toglierla, premi «Annulla rimborso» sulla stessa riga e poi
   «Conferma annullamento»: la spesa rientra nella divisione («Da rimborsare»). In alternativa, da riga
   di comando: `... cli rimborso <raw_hash> --date AAAA-MM-GG --note "..."` (`--annulla` per toglierla).
6. **Cambiare la regola di casa.** Modifica `percentuali` o `escluse` in
   `backend/config/split_config.toml` e riavvia il backend.
7. **Una spesa con quota diversa dalla regola.** Imposta la quota sulla riga in finance
   (`member_b_share_bp`, da 0 a 10000 = da 0 a 100%): vince sulla regola e sull'esclusione di categoria.
8. **Da Telegram** (sola lettura): `/saldo` e `/spese`. Il token sta nel `.env`
   (`HOMEEXPENSESPLITTER_TELEGRAM_TOKEN`).

## Servizi LLM
Il nodo non usa modelli linguistici: nessun servizio nel `config/llm-routing.json` dell'istanza. Se un
giorno servisse, si dichiara lì un servizio `homeExpenseSplitter.<funzione>` (doc Life
`docs/llm-routing.md`).

## Problemi comuni
| sintomo | causa | cosa fare |
|---|---|---|
| «Finance non è raggiungibile…» (API 503) | finance è spento o `FINANCE_URL` è sbagliato | accendere finance; nei container `FINANCE_URL=http://finance-backend:10023`. È voluto: mai un saldo su dati vecchi |
| «Non riesco a caricare le spese condivise» | finance non risponde (stesso 503 del saldo) | stessa cura: accendere finance o correggere `FINANCE_URL`, poi «Riprova» |
| saldo a 0,00 € | finance non ha uscite condivise confermate in quell'istanza | controllare i dati in finance |
| API 500, `relation "reimbursements" does not exist` | database senza le ultime migrazioni | backup `pg_dump` in `data/backups/`, poi `alembic upgrade head` (migrazioni solo additive) |
| «La vista non è disponibile» | il backend non risponde o non trova `node.config` | riavviare il backend; in container serve l'override che monta `node.config` |
| mancano «Salva saldo» o «Esporta» | il ruolo è Ospite | serve il ruolo Membro |
| percentuali sbagliate (es. 50/50) | `split_config.toml` | correggere `[percentuali]` e riavviare |
