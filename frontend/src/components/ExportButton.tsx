import { Button, Callout } from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import { useState } from "react";
import { api, ApiError } from "../lib/api";
import { describeError } from "../lib/errors";
import { DownloadIcon } from "./icons";

/** Scarica il workbook da /api/export.xlsx forzando il filename. */
export function ExportButton() {
  const { t } = useLanguage();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(api.exportXlsxUrl());
      if (!res.ok) throw new ApiError(res.status, res.statusText);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Household_Expenses.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (e) {
      setError(`${t("export.error")}. ${describeError(e, t)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-3">
      <Button className="min-h-11" onClick={download} loading={busy}>
        <DownloadIcon className="size-4" />
        {busy ? t("export.downloading") : t("export.download")}
      </Button>
      {error && <Callout variant="danger">{error}</Callout>}
    </div>
  );
}
