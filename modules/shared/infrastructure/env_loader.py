from __future__ import annotations

import os
from pathlib import Path


def load_env_file() -> None:
    """Carga backend_nexa/.env en os.environ (override=False).

    La app lee la configuración (DB_PROVIDER, COSMOS_*) desde os.environ en
    tiempo de arranque (load_config / load_app_settings). Sin esta carga, un
    .env presente en el repo no tendría efecto al lanzar el servidor.

    IMPORTANTE: se invoca SOLO desde el entrypoint __main__ (python -m
    backend_nexa.app), NO al importar el módulo. Así los tests que importan
    create_app permanecen herméticos (no heredan el .env del desarrollador) y
    el subproceso de reload de uvicorn hereda las variables vía os.environ.
    No sobrescribe variables ya definidas en el entorno real.
    """
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore[import]

        load_dotenv(env_path)
        return
    except ImportError:
        pass
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
