import { ApiError } from "./api";

/** Un errore di rete o del backend in una frase per l'utente: mai codici o dettagli tecnici. */
export function describeError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return t("errors.forbidden");
    }
    if (error.status === 503) return t("errors.unavailable");
  }
  return t("errors.generic");
}
