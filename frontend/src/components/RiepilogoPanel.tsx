import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DataTable,
  cn,
  type Column,
} from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import { useMemo, type ReactNode } from "react";
import type { SummaryOut } from "../lib/api";
import { euro } from "../lib/format";

type RowKind = "category" | "total" | "balance";

interface SummaryRow {
  key: string;
  kind: RowKind;
  label: ReactNode;
  cents: number;
}

/** Le righe di chiusura riempiono l'intera cella: la tabella le legge come righe vere. */
function Cell({ kind, children }: { kind: RowKind; children: ReactNode }) {
  if (kind === "category") return <>{children}</>;
  return (
    <span
      className={cn(
        "-mx-3 -my-2.5 block px-3 py-2.5 font-semibold text-text",
        kind === "total" && "border-t-2 border-border-strong bg-surface-2",
        kind === "balance" && "bg-accent-soft font-bold",
      )}
    >
      {children}
    </span>
  );
}

/** Ripartizione per categoria, con TOTALE DIVISIBILE e SALDO evidenziati. */
export function RiepilogoPanel({ data }: { data: SummaryOut }) {
  const { t } = useLanguage();

  const rows = useMemo<SummaryRow[]>(
    () => [
      ...data.per_category.map(([category, cents], index) => ({
        key: `category-${index}`,
        kind: "category" as const,
        label: category ?? (
          <span className="text-muted">{t("common.uncategorized")}</span>
        ),
        cents,
      })),
      {
        key: "total",
        kind: "total",
        label: t("summary.totalDivisible"),
        cents: data.divisible_cents,
      },
      {
        key: "balance",
        kind: "balance",
        label: `${t("summary.balance")} (${data.member_b_name} → ${data.member_a_name})`,
        cents: data.saldo_cents,
      },
    ],
    [data, t],
  );

  const columns = useMemo<Column<SummaryRow>[]>(
    () => [
      {
        key: "category",
        header: t("summary.category"),
        accessor: (row) => row.key,
        render: (row) => <Cell kind={row.kind}>{row.label}</Cell>,
      },
      {
        key: "amount",
        header: t("summary.amount"),
        accessor: (row) => row.cents,
        render: (row) => (
          <Cell kind={row.kind}>
            <span className="whitespace-nowrap tabular-nums">
              {euro(row.cents)}
            </span>
          </Cell>
        ),
      },
    ],
    [t],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("summary.title")}</CardTitle>
      </CardHeader>
      <CardBody className="overflow-x-auto p-0 pb-2">
        <DataTable columns={columns} data={rows} rowKey={(row) => row.key} />
      </CardBody>
    </Card>
  );
}
