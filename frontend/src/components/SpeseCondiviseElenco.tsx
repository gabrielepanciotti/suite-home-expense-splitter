import { useLanguage } from "@suite/i18n";
import type { SharedExpenseOut } from "../lib/api";
import { euro, formatDate } from "../lib/format";
import { RimborsoAzione } from "./RimborsoAzione";
import { SpesaStato } from "./SpesaStato";

interface SpeseCondiviseElencoProps {
  expenses: SharedExpenseOut[];
  canAct: boolean;
  onChanged: () => void;
}

/** Le spese come elenco di schede: sotto `md` la tabella non entra e le azioni finirebbero fuori schermo. */
export function SpeseCondiviseElenco({
  expenses,
  canAct,
  onChanged,
}: SpeseCondiviseElencoProps) {
  const { language, t } = useLanguage();

  return (
    <ul className="divide-y divide-border">
      {expenses.map((expense) => (
        <li key={expense.raw_hash} className="flex flex-col gap-2 p-4">
          <div className="flex items-start justify-between gap-3">
            <span className="min-w-0 break-words font-medium text-text">
              {expense.description}
            </span>
            <span className="flex-none whitespace-nowrap font-semibold tabular-nums text-text">
              {euro(expense.amount_cents)}
            </span>
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
            <dt className="text-muted">{t("sharedExpenses.date")}</dt>
            <dd className="text-text-2">{formatDate(expense.date, language)}</dd>
            <dt className="text-muted">{t("sharedExpenses.category")}</dt>
            <dd className="min-w-0 break-words text-text-2">
              {expense.category ?? t("common.uncategorized")}
            </dd>
          </dl>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SpesaStato expense={expense} />
            {canAct && (
              <RimborsoAzione expense={expense} onChanged={onChanged} />
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
