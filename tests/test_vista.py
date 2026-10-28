"""Role-aware view integration tests without database or network access."""

from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from home_expense_splitter_backend.app import app
from home_expense_splitter_backend.claims import claims_dependency
from home_expense_splitter_backend import db
from home_expense_splitter_backend.vista import vista_spec
from suite_backend_core.gate import GateClaims
from suite_backend_core.vista import MemoryPreferenceStore, make_vista_router


def _claims(role: str) -> GateClaims:
    return GateClaims(
        person_id="vista-test-user",
        instance="homeExpenseSplitter",
        role=role,
        kind="person",
    )


async def _request(app: FastAPI, method: str, path: str, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.anyio
async def test_admin_vista_has_all_sections() -> None:
    async def admin_claims() -> GateClaims:
        return _claims("admin")

    app.dependency_overrides[claims_dependency] = admin_claims
    try:
        response = await _request(app, "GET", "/api/vista")
        assert response.status_code == 200
        assert [section["id"] for section in response.json()["sezioni"]] == [
            "saldo",
            "spese",
            "esporta",
        ]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_player_sees_two_sections_and_cannot_save_settlement() -> None:

    async def player_claims() -> GateClaims:
        return _claims("player")

    app.dependency_overrides[claims_dependency] = player_claims
    try:
        vista = await _request(app, "GET", "/api/vista")
        denied = await _request(
            app,
            "POST",
            "/api/settlements",
            json={"at": None, "member_b_owes_cents": 100, "note": None},
        )
        assert [section["id"] for section in vista.json()["sezioni"]] == ["saldo", "spese"]
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("database_url", "expected_url"),
    [
        ("sqlite:///preferences.db", "sqlite+aiosqlite:///preferences.db"),
        ("postgresql://user:password@localhost/preferences", "postgresql+psycopg://user:password@localhost/preferences"),
        ("postgresql+psycopg2://user:password@localhost/preferences", "postgresql+psycopg://user:password@localhost/preferences"),
    ],
)
def test_preference_database_url_uses_async_driver(monkeypatch, database_url: str, expected_url: str) -> None:
    monkeypatch.setattr(db, "DATABASE_URL", database_url)
    monkeypatch.setattr(db, "find_spec", lambda _: object())

    assert db._preference_database_url() == expected_url


@pytest.mark.anyio
async def test_preferences_are_saved_and_restored_in_memory() -> None:
    async def creator_claims() -> GateClaims:
        return _claims("creator")

    vista_app = FastAPI()
    vista_app.include_router(
        make_vista_router(
            vista_spec,
            MemoryPreferenceStore(),
            creator_claims,
            "homeExpenseSplitter",
        )
    )
    saved = await _request(
        vista_app,
        "PUT",
        "/api/vista/preferenze",
        json={"nascoste": ["spese"], "ordine": ["esporta"], "preferiti": ["esporta"]},
    )
    restored = await _request(vista_app, "GET", "/api/vista")

    assert saved.status_code == 200
    assert restored.json()["preferenze"] == saved.json()["preferenze"]
