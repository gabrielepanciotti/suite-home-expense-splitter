"""Caller claims for the role-aware API: the shared Life dependency (Life#227)."""

from __future__ import annotations

from suite_backend_core.vista_claims import make_claims_dependency

claims_dependency = make_claims_dependency("homeExpenseSplitter")
