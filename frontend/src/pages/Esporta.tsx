import { Card, CardBody, Consentito, PageHeader } from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import { ExportButton } from "../components/ExportButton";
import { DownloadIcon } from "../components/icons";

/** Sezione `esporta`: il solo foglio Riepilogo Finale (i dettagli li esporta finance). */
export function Esporta() {
  const { t } = useLanguage();

  return (
    <section className="flex min-w-0 flex-col gap-4">
      <PageHeader
        icon={<DownloadIcon />}
        title={t("export.title")}
        subtitle={t("export.subtitle")}
      />
      <Card>
        <CardBody className="flex flex-col gap-4 py-5">
          <p className="text-sm text-text-2">{t("export.description")}</p>
          <Consentito azione="export.scarica">
            <ExportButton />
          </Consentito>
        </CardBody>
      </Card>
    </section>
  );
}
