import type { VistaBody, VistaFetcher } from "@suite/design-system";
import { LanguageProvider } from "@suite/i18n";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HomeExpenseSplitterApp } from "./App";
import en from "./i18n/en";
import it_ from "./i18n/it";
import type { SharedExpenseOut, SummaryOut } from "./lib/api";
import { fallbackVistaFetcher } from "./vistaFallback";

const SECTIONS = [
  { id: "saldo", titolo: "Saldo", nascosta: false, preferita: false },
  { id: "spese", titolo: "Spese condivise", nascosta: false, preferita: false },
  { id: "esporta", titolo: "Esporta", nascosta: false, preferita: false },
];

const ADMIN_ACTIONS = {
  "saldo.salva": true,
  "rimborso.segna": true,
  "rimborso.annulla": true,
  "export.scarica": true,
};
const PLAYER_ACTIONS = {
  "saldo.salva": false,
  "rimborso.segna": false,
  "rimborso.annulla": false,
  "export.scarica": false,
};

function vista(role: "player" | "admin"): VistaBody {
  const admin = role === "admin";
  const sezioni = admin ? SECTIONS : SECTIONS.slice(0, 2);
  return {
    ruolo: role,
    etichetta: admin ? "Proprietario" : "Ospite",
    sezioni,
    azioni: admin ? ADMIN_ACTIONS : PLAYER_ACTIONS,
    preferenze: {
      nascoste: [],
      ordine: sezioni.map((item) => item.id),
      preferiti: [],
    },
  };
}

const SUMMARY: SummaryOut = {
  saldo_cents: 12345,
  divisible_cents: 50000,
  member_b_quota_cents: 25000,
  net_bonifici_cents: 12345,
  member_a_pct: 50,
  member_b_pct: 50,
  member_a_name: "Anna",
  member_b_name: "Bruno",
  per_category: [
    ["Casa", 30000],
    [null, 20000],
  ],
};

const EXPENSES: SharedExpenseOut[] = [
  {
    raw_hash: "h1",
    date: "2026-02-01",
    description: "Bolletta luce",
    category: "Casa",
    amount_cents: 8000,
    member_b_share_bp: null,
    reimbursed: false,
    reimbursed_at: null,
    reimbursed_note: null,
  },
  {
    raw_hash: "h2",
    date: "2026-02-03",
    description: "Spesa alimentari",
    category: null,
    amount_cents: 4500,
    member_b_share_bp: null,
    reimbursed: true,
    reimbursed_at: "2026-02-05",
    reimbursed_note: null,
  },
];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function vistaFetcher(body: VistaBody): VistaFetcher {
  return vi.fn(async () => json(body));
}

function stubApi(overrides: { summary?: Response; expenses?: Response } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.includes("/api/summary")) {
        return overrides.summary ?? json(SUMMARY);
      }
      if (url.includes("/api/shared-expenses")) {
        return overrides.expenses ?? json(EXPENSES);
      }
      return json({}, 404);
    }),
  );
}

function renderApp(fetcher: VistaFetcher, hash = "#saldo") {
  window.location.hash = hash;
  return render(
    <LanguageProvider translations={{ en, it: it_ }} defaultLanguage="it">
      <HomeExpenseSplitterApp vistaFetcher={fetcher} />
    </LanguageProvider>,
  );
}

/** Le voci di navigazione, senza il pulsante che comprime la barra. */
async function navigationItems() {
  const nav = await screen.findByRole("navigation");
  return within(nav)
    .getAllByRole("button")
    .map((button) => button.getAttribute("aria-label"))
    .filter((label) => label && !/barra laterale/i.test(label));
}

beforeEach(() => {
  stubApi();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HomeExpenseSplitter vista", () => {
  it("ruolo admin: tre voci di navigazione e «Salva saldo»", async () => {
    renderApp(vistaFetcher(vista("admin")));

    expect(await navigationItems()).toEqual([
      "Saldo",
      "Spese condivise",
      "Esporta",
    ]);
    expect(
      await screen.findByRole("button", { name: "Salva saldo" }),
    ).toBeInTheDocument();
  });

  it("ruolo player: due voci e niente «Salva saldo»", async () => {
    renderApp(vistaFetcher(vista("player")));

    expect(await navigationItems()).toEqual(["Saldo", "Spese condivise"]);
    // il saldo è già caricato: l'assenza del pulsante non dipende dall'attesa
    expect(await screen.findByText(/Bruno deve a Anna/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Salva saldo" }),
    ).not.toBeInTheDocument();
  });

  it("mostra il riepilogo con totale divisibile e saldo", async () => {
    renderApp(vistaFetcher(vista("admin")));

    expect(await screen.findByText("Riepilogo divisione")).toBeInTheDocument();
    expect(screen.getByText("Saldo (Bruno → Anna)")).toBeInTheDocument();
    expect(screen.getAllByText("Totale divisibile").length).toBeGreaterThan(0);
    expect(screen.getByText("(senza categoria)")).toBeInTheDocument();
  });

  it("spese: le azioni sul rimborso seguono il ruolo", async () => {
    const { unmount } = renderApp(vistaFetcher(vista("admin")), "#spese");
    expect(
      await screen.findByRole("button", { name: "Segna rimborsata" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Annulla rimborso" }),
    ).toBeInTheDocument();
    unmount();

    renderApp(vistaFetcher(vista("player")), "#spese");
    expect(await screen.findByText("Bolletta luce")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Segna rimborsata" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Azioni" }),
    ).not.toBeInTheDocument();
  });

  it("a 360 px le spese diventano schede con le azioni a portata", async () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    renderApp(vistaFetcher(vista("admin")), "#spese");

    expect(await screen.findByText("Bolletta luce")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Segna rimborsata" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Annulla rimborso" }),
    ).toBeInTheDocument();
  });

  it("esporta: il pulsante di download c'è per chi può scaricare", async () => {
    renderApp(vistaFetcher(vista("admin")), "#esporta");
    expect(
      await screen.findByRole("button", { name: "Scarica Excel" }),
    ).toBeInTheDocument();
  });

  it("la navigazione cambia sezione", async () => {
    renderApp(vistaFetcher(vista("admin")));
    await userEvent.click(
      await screen.findByRole("button", { name: "Spese condivise" }),
    );
    expect(await screen.findByText("Bolletta luce")).toBeInTheDocument();
    expect(window.location.hash).toBe("#spese");
  });

  it.each([401, 500])(
    "usa la vista in sola lettura quando /api/vista risponde %i",
    async (status) => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async (url: string) => {
          if (url.includes("/api/vista")) return json({}, status);
          if (url.includes("/api/summary")) return json(SUMMARY);
          if (url.includes("/api/shared-expenses")) return json(EXPENSES);
          return json({}, 404);
        }),
      );
      renderApp(fallbackVistaFetcher);

      expect(await navigationItems()).toContain("Saldo");
      expect(screen.getByText(/Sola lettura/)).toBeInTheDocument();
    },
  );

  it("vista non disponibile: errore con «Riprova» se il fetcher fallisce", async () => {
    let calls = 0;
    const fetcher: VistaFetcher = vi.fn(async () => {
      calls += 1;
      if (calls === 1) throw new Error("vista non disponibile");
      return json(vista("admin"));
    });
    renderApp(fetcher);

    expect(
      await screen.findByText("La vista non è disponibile"),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Riprova" }));
    await waitFor(async () =>
      expect(await navigationItems()).toContain("Saldo"),
    );
  });

  it("saldo non calcolabile: errore in italiano, senza codici, con «Riprova»", async () => {
    stubApi({ summary: json({ detail: "finance down" }, 503) });
    renderApp(vistaFetcher(vista("admin")));

    expect(
      await screen.findByText("Non riesco a calcolare il saldo"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Finance non è raggiungibile/)).toBeInTheDocument();
    expect(screen.queryByText(/503|finance down/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Riprova" })).toBeInTheDocument();
  });

  it("nessuna spesa condivisa: stato vuoto con l'azione «Ricarica»", async () => {
    stubApi({ expenses: json([]) });
    renderApp(vistaFetcher(vista("admin")), "#spese");

    expect(await screen.findByText("Nessuna spesa condivisa")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ricarica" })).toBeInTheDocument();
  });
});
