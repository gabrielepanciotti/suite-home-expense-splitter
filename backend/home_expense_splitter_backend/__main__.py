# Entrypoint canone Life: `python -m home_expense_splitter_backend` avvia uvicorn su $PORT (default 10009).
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "home_expense_splitter_backend.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10009")),
    )


if __name__ == "__main__":
    main()
