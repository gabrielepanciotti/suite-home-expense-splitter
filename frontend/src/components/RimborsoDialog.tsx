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
import { api, type SharedExpenseOut } from "../lib/api";
import { describeError } from "../lib/errors";
import { isoLocalDate } from "../lib/format";

interface RimborsoDialogProps {
  expense: SharedExpenseOut;
  onChanged: () => void;
}

export function RimborsoDialog({ expense, onChanged }: RimborsoDialogProps) {
  const { locale, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [undo, setUndo] = useState(expense.reimbursed);
  const [date, setDate] = useState<Date | undefined>(() => new Date());
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen) {
      setUndo(expense.reimbursed);
      setDate(new Date());
      setNote("");
      setError(null);
      setDone(false);
    }
  }

  async function handleSubmit() {
    if (!undo && !date) {
      setError(t("reimbursements.dateRequired"));
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (undo) {
        await api.deleteReimbursement(expense.raw_hash);
      } else {
        await api.putReimbursement({
          raw_hash: expense.raw_hash,
          at: isoLocalDate(date as Date),
          note: note.trim() || null,
        });
      }
      setDone(true);
      onChanged();
    } catch (error) {
      setError(describeError(error, t));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          type="button"
          size="sm"
          className="min-h-11"
          variant={expense.reimbursed ? "destructive" : "secondary"}
        >
          {expense.reimbursed
            ? t("reimbursements.undo")
            : t("reimbursements.mark")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {undo
              ? t("reimbursements.undoTitle")
              : t("reimbursements.markTitle")}
          </DialogTitle>
          <DialogDescription>
            {undo
              ? t("reimbursements.undoDescription")
              : t("reimbursements.markDescription")}
          </DialogDescription>
        </DialogHeader>

        <p className="rounded-card border border-border bg-surface-2 p-3 text-sm text-text">
          {expense.description}
        </p>

        {!undo && (
          <>
            <Field
              label={t("reimbursements.date")}
              htmlFor={`reimbursement-date-${expense.raw_hash}`}
              required
            >
              <DatePicker
                id={`reimbursement-date-${expense.raw_hash}`}
                className="min-h-11"
                value={date}
                locale={locale}
                onChange={setDate}
                disabled={submitting || done}
                placeholder={t("reimbursements.datePlaceholder")}
                aria-label={t("reimbursements.date")}
              />
            </Field>
            <Field
              label={t("reimbursements.note")}
              htmlFor={`reimbursement-note-${expense.raw_hash}`}
            >
              <Textarea
                id={`reimbursement-note-${expense.raw_hash}`}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                disabled={submitting || done}
                rows={3}
                placeholder={t("reimbursements.notePlaceholder")}
              />
            </Field>
          </>
        )}

        {error && <Callout variant="danger">{error}</Callout>}
        {done && (
          <Callout variant="success">
            {undo
              ? t("reimbursements.undoSuccess")
              : t("reimbursements.markSuccess")}
          </Callout>
        )}

        <DialogFooter className="flex-col-reverse sm:flex-row">
          <Button
            type="button"
            variant="secondary"
            className="min-h-11"
            onClick={() => setOpen(false)}
          >
            {done ? t("common.close") : t("common.cancel")}
          </Button>
          {!done && (
            <Button
              type="button"
              variant={undo ? "destructive" : "primary"}
              className="min-h-11"
              loading={submitting}
              onClick={handleSubmit}
            >
              {submitting
                ? t("common.saving")
                : undo
                  ? t("reimbursements.undoConfirm")
                  : t("reimbursements.markConfirm")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
