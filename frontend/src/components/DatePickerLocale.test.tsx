import * as designSystem from "@suite/design-system";
import { LanguageProvider } from "@suite/i18n";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../i18n/en";
import it_ from "../i18n/it";
import type { SharedExpenseOut } from "../lib/api";
import { RimborsoDialog } from "./RimborsoDialog";
import { SalvaSaldoDialog } from "./SalvaSaldoDialog";

// Record the props each DatePicker receives while still rendering the real one:
// `locale` drives both the formatted value and the calendar (month names, week start).
const datePickerProps = vi.hoisted(() => [] as Array<{ locale?: string }>);
vi.mock("@suite/design-system", async (importOriginal) => {
  const actual = await importOriginal<typeof designSystem>();
  return {
    ...actual,
    DatePicker: (props: designSystem.DatePickerProps) => {
      datePickerProps.push(props);
      return <actual.DatePicker {...props} />;
    },
  };
});

// Both dialogs default the date to "today": pin it so the formatted value is stable.
const TODAY = new Date(2026, 1, 10, 12);

const expense: SharedExpenseOut = {
  raw_hash: "abc123",
  date: "2026-02-01",
  description: "Spesa",
  category: null,
  amount_cents: 1000,
  member_b_share_bp: null,
  reimbursed: false,
  reimbursed_at: null,
  reimbursed_note: null,
};

function renderIn(language: "en" | "it", ui: ReactNode) {
  return render(
    <LanguageProvider translations={{ en, it: it_ }} defaultLanguage={language}>
      {ui}
    </LanguageProvider>,
  );
}

const cases = [
  {
    name: "SalvaSaldoDialog",
    ui: <SalvaSaldoDialog saldoCents={1234} onSaved={() => undefined} />,
    open: { en: "Save balance", it: "Salva saldo" },
    date: { en: "Date", it: "Data" },
  },
  {
    name: "RimborsoDialog",
    ui: <RimborsoDialog expense={expense} onChanged={() => undefined} />,
    open: { en: "Mark reimbursed", it: "Segna rimborsata" },
    date: { en: "Reimbursement date", it: "Data del rimborso" },
  },
];

const expected = {
  en: { locale: "en-US", value: "02/10/2026" },
  it: { locale: "it-IT", value: "10/02/2026" },
} as const;

describe.each(cases)("$name DatePicker", ({ ui, open, date }) => {
  beforeEach(() => {
    datePickerProps.length = 0;
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(TODAY);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it.each(["en", "it"] as const)(
    "follows the active language (%s)",
    async (language) => {
      renderIn(language, ui);
      await userEvent.click(
        screen.getByRole("button", { name: open[language] }),
      );

      expect(
        screen.getByRole("button", { name: date[language] }),
      ).toHaveTextContent(expected[language].value);
      expect(datePickerProps.length).toBeGreaterThan(0);
      for (const props of datePickerProps) {
        expect(props.locale).toBe(expected[language].locale);
      }
    },
  );
});
