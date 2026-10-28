import { Badge } from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import type { SharedExpenseOut } from "../lib/api";
import { formatDate } from "../lib/format";

/** Rimborsata (con data) oppure da rimborsare. */
export function SpesaStato({ expense }: { expense: SharedExpenseOut }) {
  const { language, t } = useLanguage();
  return expense.reimbursed ? (
    <Badge state="success" dot className="whitespace-nowrap">
      {t("sharedExpenses.reimbursed")} ·{" "}
      {formatDate(expense.reimbursed_at, language)}
    </Badge>
  ) : (
    <Badge className="whitespace-nowrap">{t("sharedExpenses.pending")}</Badge>
  );
}
