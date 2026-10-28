// Typed API client for the HomeExpenseSplitter dashboard.
// Contract mirrors home_expense_splitter_backend/schemas.py exactly. Amounts are integer CENTS.

// Default "" = same-origin relative URLs (/api/...), forwarded to the backend by the
// Vite dev-server proxy (see vite.config.ts). Override with VITE_API_URL only to hit an
// absolute backend origin directly.
export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "";

// --- DTOs -------------------------------------------------------------------
export interface SummaryOut {
  saldo_cents: number;
  divisible_cents: number;
  member_b_quota_cents: number;
  net_bonifici_cents: number;
  member_a_pct: number;
  member_b_pct: number;
  // Display names come from the backend: generic defaults ("Member A"/"Member B"),
  // device-local aliases via the untracked MEMBER_ALIASES_JSON env var.
  member_a_name: string;
  member_b_name: string;
  per_category: [string | null, number][];
}

export interface SettlementCreate {
  at: string | null;
  member_b_owes_cents: number;
  note: string | null;
}

export interface SettlementCreated {
  id: number;
}

export interface SharedExpenseOut {
  raw_hash: string;
  date: string;
  description: string;
  category: string | null;
  amount_cents: number;
  member_b_share_bp: number | null;
  reimbursed: boolean;
  reimbursed_at: string | null;
  reimbursed_note: string | null;
}

export interface ReimbursementUpsert {
  raw_hash: string;
  at: string;
  note: string | null;
}

// --- low-level fetch helpers ------------------------------------------------
class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail)
        detail =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- API surface ------------------------------------------------------------
export const api = {
  getSummary: () => request<SummaryOut>("/api/summary"),

  createSettlement: (body: SettlementCreate) =>
    request<SettlementCreated>("/api/settlements", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getSharedExpenses: () =>
    request<SharedExpenseOut[]>("/api/shared-expenses"),

  putReimbursement: (body: ReimbursementUpsert) =>
    request<void>("/api/reimbursements", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteReimbursement: (rawHash: string) =>
    request<void>(`/api/reimbursements/${encodeURIComponent(rawHash)}`, {
      method: "DELETE",
    }),

  exportXlsxUrl: () => `${API_URL}/api/export.xlsx`,
};

export { ApiError };
