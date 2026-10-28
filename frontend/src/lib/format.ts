// Formatting helpers — amounts are integer cents.

const eurFmt = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numFmt = new Intl.NumberFormat("it-IT", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** cents -> "€ 1.234,56" */
export function euro(cents: number): string {
  return eurFmt.format(cents / 100);
}

/** cents -> "1.234,56" (no symbol) */
export function euroPlain(cents: number): string {
  return numFmt.format(cents / 100);
}

/** ISO/null date -> localized calendar date. */
export function formatDate(iso: string | null, language: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(language === "it" ? "it-IT" : "en-GB");
}

/** Local Date -> "YYYY-MM-DD", without UTC timezone shifts. */
export function isoLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** "YYYY-MM" -> "mmm yyyy" (it) */
export function formatMonth(month: string): string {
  const [y, m] = month.split("-").map(Number);
  if (!y || !m) return month;
  return new Date(y, m - 1, 1).toLocaleDateString("it-IT", {
    month: "short",
    year: "numeric",
  });
}
