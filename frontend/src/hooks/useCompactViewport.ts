import { useEffect, useState } from "react";

/** Sotto `md` (768 px) la barra laterale si sovrappone al contenuto e le tabelle larghe non entrano. */
const COMPACT_QUERY = "(max-width: 767px)";

const read = () =>
  typeof window.matchMedia === "function"
    ? window.matchMedia(COMPACT_QUERY)
    : null;

export function useCompactViewport(): boolean {
  const [compact, setCompact] = useState(() => read()?.matches ?? false);

  useEffect(() => {
    const query = read();
    if (!query) return;
    const update = () => setCompact(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return compact;
}
