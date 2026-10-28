import {
  Button,
  Card,
  CardBody,
  DataTable,
  EmptyState,
  Spinner,
  useVista,
  type Column,
} from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import { useMemo } from "react";
import { useCompactViewport } from "../hooks/useCompactViewport";
import type { UseSharedExpensesResult } from "../hooks/useSharedExpenses";
import type { SharedExpenseOut } from "../lib/api";
import { describeError } from "../lib/errors";
import { euro, formatDate } from "../lib/format";
import { AlertIcon, InboxIcon } from "./icons";
import { RimborsoAzione } from "./RimborsoAzione";
import { SpeseCondiviseElenco } from "./SpeseCondiviseElenco";
import { SpesaStato } from "./SpesaStato";

interface SpeseCondivisePanelProps {
  expenses: UseSharedExpensesResult;
}

export function SpeseCondivisePanel({ expenses }: SpeseCondivisePanelProps) {
  const { language, t } = useLanguage();
  const { puo } = useVista();
  const compact = useCompactViewport();
  const { refresh } = expenses;
  const canAct = puo("rimborso.segna") || puo("rimborso.annulla");

  const columns = useMemo<Column<SharedExpenseOut>[]>(() => {
    const base: Column<SharedExpenseOut>[] = [
      {
        key: "date",
        header: t("sharedExpenses.date"),
        sortable: true,
        accessor: (row) => row.date,
        render: (row) => (
          <span className="whitespace-nowrap text-text-2">
            {formatDate(row.date, language)}
          </span>
        ),
      },
      {
        key: "description",
        header: t("sharedExpenses.description"),
        sortable: true,
        accessor: (row) => row.description,
        render: (row) => (
          <span className="block min-w-48 font-medium text-text">
            {row.description}
          </span>
        ),
      },
      {
        key: "category",
        header: t("sharedExpenses.category"),
        sortable: true,
        accessor: (row) => row.category ?? "",
        render: (row) => (
          <span className="whitespace-nowrap">
            {row.category ?? (
              <span className="text-muted">{t("common.uncategorized")}</span>
            )}
          </span>
        ),
      },
      {
        key: "amount",
        header: t("sharedExpenses.amount"),
        sortable: true,
        accessor: (row) => row.amount_cents,
        render: (row) => (
          <span className="whitespace-nowrap tabular-nums text-text">
            {euro(row.amount_cents)}
          </span>
        ),
      },
      {
        key: "status",
        header: t("sharedExpenses.status"),
        accessor: (row) => (row.reimbursed ? 1 : 0),
        render: (row) => <SpesaStato expense={row} />,
      },
    ];
    if (!canAct) return base;
    return [
      ...base,
      {
        key: "actions",
        header: t("sharedExpenses.actions"),
        accessor: (row) => row.raw_hash,
        render: (row) => <RimborsoAzione expense={row} onChanged={refresh} />,
      },
    ];
  }, [canAct, language, refresh, t]);

  if (expenses.error) {
    return (
      <Card>
        <EmptyState
          icon={<AlertIcon />}
          title={t("sharedExpenses.loadError")}
          description={describeError(expenses.error, t)}
          glow={false}
          action={
            <Button className="min-h-11" onClick={refresh}>
              {t("common.retry")}
            </Button>
          }
        />
      </Card>
    );
  }

  // Spinner solo al primo caricamento: durante un ricarico la tabella resta, così
  // il dialog che ha appena salvato non si smonta prima di mostrare l'esito.
  if (expenses.loading && expenses.data.length === 0) {
    return (
      <Card>
        <CardBody
          className="flex min-h-48 items-center justify-center gap-3 text-muted"
          role="status"
        >
          <Spinner />
          <span>{t("sharedExpenses.loading")}</span>
        </CardBody>
      </Card>
    );
  }

  if (expenses.data.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<InboxIcon />}
          title={t("sharedExpenses.empty")}
          description={t("sharedExpenses.emptyDescription")}
          glow={false}
          action={
            <Button
              variant="secondary"
              className="min-h-11"
              onClick={refresh}
            >
              {t("common.reload")}
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <Card>
      <CardBody className="overflow-x-auto p-0">
        {compact ? (
          <SpeseCondiviseElenco
            expenses={expenses.data}
            canAct={canAct}
            onChanged={refresh}
          />
        ) : (
          <DataTable
            columns={columns}
            data={expenses.data}
            rowKey={(row) => row.raw_hash}
            className="[&_th_button]:min-h-11"
          />
        )}
      </CardBody>
    </Card>
  );
}
