import { Consentito } from "@suite/design-system";
import type { SharedExpenseOut } from "../lib/api";
import { RimborsoDialog } from "./RimborsoDialog";

interface RimborsoAzioneProps {
  expense: SharedExpenseOut;
  onChanged: () => void;
}

/** Segna o annulla il rimborso, solo se il ruolo ha l'azione corrispondente. */
export function RimborsoAzione({ expense, onChanged }: RimborsoAzioneProps) {
  return (
    <Consentito
      azione={expense.reimbursed ? "rimborso.annulla" : "rimborso.segna"}
    >
      <RimborsoDialog expense={expense} onChanged={onChanged} />
    </Consentito>
  );
}
