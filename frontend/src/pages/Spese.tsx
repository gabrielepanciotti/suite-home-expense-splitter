import { PageHeader } from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import { ListIcon } from "../components/icons";
import { SpeseCondivisePanel } from "../components/SpeseCondivisePanel";
import { useSharedExpenses } from "../hooks/useSharedExpenses";

/** Sezione `spese`: le spese condivise confermate e il loro stato di rimborso. */
export function Spese() {
  const { t } = useLanguage();
  const expenses = useSharedExpenses();

  return (
    <section className="flex min-w-0 flex-col gap-4">
      <PageHeader
        icon={<ListIcon />}
        title={t("sharedExpenses.title")}
        subtitle={t("sharedExpenses.descriptionText")}
      />
      <SpeseCondivisePanel expenses={expenses} />
    </section>
  );
}
