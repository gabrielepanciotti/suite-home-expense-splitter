import type { VistaBody, VistaFetcher } from "@suite/design-system";

// Mirrors the player-visible entries in node.config vista.sezioni, in the same order.
const PLAYER_SECTIONS: VistaBody["sezioni"] = [
  { id: "saldo", titolo: "Saldo", nascosta: false, preferita: false },
  {
    id: "spese",
    titolo: "Spese condivise",
    nascosta: false,
    preferita: false,
  },
];

const READ_ONLY_VISTA: VistaBody = {
  ruolo: "player",
  etichetta: "Sola lettura",
  sezioni: PLAYER_SECTIONS,
  azioni: {},
  preferenze: {
    nascoste: [],
    ordine: [],
    preferiti: [],
  },
};

let hasWarned = false;

function warnOnce(reason: unknown) {
  if (hasWarned) return;
  hasWarned = true;
  console.warn("Vista non disponibile: uso la navigazione in sola lettura.", reason);
}

function readOnlyResponse() {
  return new Response(JSON.stringify(READ_ONLY_VISTA), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

export const fallbackVistaFetcher: VistaFetcher = async (input, init) => {
  if (init?.method && init.method.toUpperCase() !== "GET") {
    return fetch(input, init);
  }

  try {
    const response = await fetch(input, init);
    if (response.ok) return response;
    warnOnce(`HTTP ${response.status}`);
  } catch (error) {
    warnOnce(error);
  }

  return readOnlyResponse();
};
