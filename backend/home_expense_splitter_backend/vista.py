"""HomeExpenseSplitter's declared role-aware view."""

from __future__ import annotations

import json
from pathlib import Path

from suite_backend_core.vista import VistaSpec


def load_vista_spec() -> VistaSpec:
    # In the container node.config is mounted at /app/node.config by
    # deploy/docker-compose.override.yml (the generated image copies only backend/).
    node_config = Path(__file__).resolve().parents[2] / "node.config"
    return VistaSpec.from_node_config(json.loads(node_config.read_text(encoding="utf-8")))


vista_spec = load_vista_spec()
