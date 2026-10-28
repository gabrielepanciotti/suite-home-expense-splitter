import {
  Button,
  Card,
  CardBody,
  EmptyState,
  PageHeader,
  Spinner,
} from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import type { ReactNode } from "react";
import { AlertIcon, ScaleIcon } from "../components/icons";
import { RiepilogoPanel } from "../components/RiepilogoPanel";
import { SaldoHeader } from "../components/SaldoHeader";
import { useSummary } from "../hooks/useSummary";
import { describeError } from "../lib/errors";

/** Sezione `saldo`: chi deve a chi e come si compone il totale. */
export function Saldo() {
  const { t } = useLanguage();
  const { data, loading, error, refresh } = useSummary();

  let body: ReactNode;
  if (error || (!data && !loading)) {
    body = (
      <Card>
        <EmptyState
          icon={<AlertIcon />}
          title={t("balance.loadError")}
          description={error ? describeError(error, t) : t("common.missingData")}
          glow={false}
          action={
            <Button className="min-h-11" onClick={refresh}>
              {t("common.retry")}
            </Button>
          }
        />
      </Card>
    );
  } else if (!data) {
    body = (
      <Card>
        <CardBody
          className="flex min-h-48 items-center justify-center gap-3 text-muted"
          role="status"
        >
          <Spinner />
          <span>{t("balance.loadingBalance")}</span>
        </CardBody>
      </Card>
    );
  } else {
    // Durante un ricarico i dati restano: il dialog che ha appena salvato non si smonta.
    body = (
      <>
        <SaldoHeader data={data} onSaved={refresh} />
        <RiepilogoPanel data={data} />
      </>
    );
  }

  return (
    <section className="flex min-w-0 flex-col gap-4">
      <PageHeader
        icon={<ScaleIcon />}
        title={t("balance.pageTitle")}
        subtitle={t("balance.pageSubtitle")}
      />
      {body}
    </section>
  );
}
