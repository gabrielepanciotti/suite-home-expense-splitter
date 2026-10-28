import { Card, CardBody, Consentito } from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import type { SummaryOut } from "../lib/api";
import { euro } from "../lib/format";
import { SalvaSaldoDialog } from "./SalvaSaldoDialog";

interface SaldoHeaderProps {
  data: SummaryOut;
  onSaved: () => void;
}

/** Chi deve a chi, in grande, più le tre cifre che lo compongono. */
export function SaldoHeader({ data, onSaved }: SaldoHeaderProps) {
  const { t } = useLanguage();
  const positive = data.saldo_cents >= 0;

  return (
    <Card>
      <CardBody className="flex flex-col gap-5 py-5">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:gap-6">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              {t("balance.sectionLabel")}
            </p>
            <h2 className="mt-2 break-words text-2xl font-semibold text-text sm:text-3xl">
              {positive ? (
                <>
                  {data.member_b_name} {t("balance.owes")} {data.member_a_name}{" "}
                  <span className="text-success">{euro(data.saldo_cents)}</span>
                </>
              ) : (
                <>
                  {data.member_a_name} {t("balance.owes")} {data.member_b_name}{" "}
                  <span className="text-danger">
                    {euro(Math.abs(data.saldo_cents))}
                  </span>
                </>
              )}
            </h2>
          </div>
          <Consentito azione="saldo.salva">
            <div className="w-full flex-none sm:w-auto">
              <SalvaSaldoDialog saldoCents={data.saldo_cents} onSaved={onSaved} />
            </div>
          </Consentito>
        </div>

        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Stat
            label={t("balance.totalDivisible")}
            value={euro(data.divisible_cents)}
          />
          <Stat
            label={`${t("balance.share")} ${data.member_b_name} (${data.member_b_pct}%)`}
            value={euro(data.member_b_quota_cents)}
          />
          <Stat
            label={t("balance.netTransfers")}
            value={euro(data.net_bonifici_cents)}
          />
        </dl>
      </CardBody>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-card border border-border bg-surface-2 px-4 py-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-1 break-words text-lg font-semibold tabular-nums text-text">
        {value}
      </dd>
    </div>
  );
}
