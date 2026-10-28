import {
  Button,
  Callout,
  DatePicker,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Field,
  Textarea,
} from "@suite/design-system";
import { useLanguage } from "@suite/i18n";
import { useState } from "react";
import { api } from "../lib/api";
import { describeError } from "../lib/errors";
import { euro, isoLocalDate } from "../lib/format";

interface SalvaSaldoDialogProps {
  saldoCents: number;
  onSaved: () => void;
}

export function SalvaSaldoDialog({
  saldoCents,
  onSaved,
}: SalvaSaldoDialogProps) {
  const { locale, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [amountCents, setAmountCents] = useState(saldoCents);
  const [date, setDate] = useState<Date | undefined>(() => new Date());
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen) {
      setAmountCents(saldoCents);
      setDate(new Date());
      setNote("");
      setError(null);
      setSaved(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.createSettlement({
        at: date ? isoLocalDate(date) : null,
        member_b_owes_cents: amountCents,
        note: note.trim() || null,
      });
      setSaved(true);
      onSaved();
    } catch (error) {
      setError(describeError(error, t));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button type="button" className="min-h-11 w-full sm:w-auto">
          {t("settlement.open")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("settlement.title")}</DialogTitle>
          <DialogDescription>{t("settlement.description")}</DialogDescription>
        </DialogHeader>

        <div className="rounded-card border border-border bg-surface-2 p-4">
          <p className="text-xs text-muted">{t("settlement.amount")}</p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-text">
            {euro(amountCents)}
          </p>
        </div>

        <Field label={t("settlement.date")} htmlFor="settlement-date">
          <DatePicker
            id="settlement-date"
            className="min-h-11"
            value={date}
            locale={locale}
            onChange={setDate}
            disabled={saving || saved}
            placeholder={t("settlement.datePlaceholder")}
            aria-label={t("settlement.date")}
          />
        </Field>
        <Field label={t("settlement.note")} htmlFor="settlement-note">
          <Textarea
            id="settlement-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            disabled={saving || saved}
            rows={3}
            placeholder={t("settlement.notePlaceholder")}
          />
        </Field>

        {error && <Callout variant="danger">{error}</Callout>}
        {saved && (
          <Callout variant="success">{t("settlement.success")}</Callout>
        )}

        <DialogFooter className="flex-col-reverse sm:flex-row">
          <Button
            type="button"
            variant="secondary"
            className="min-h-11"
            onClick={() => setOpen(false)}
          >
            {saved ? t("common.close") : t("common.cancel")}
          </Button>
          {!saved && (
            <Button
              type="button"
              className="min-h-11"
              loading={saving}
              onClick={handleSave}
            >
              {saving ? t("settlement.saving") : t("settlement.confirm")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
