#!/usr/bin/env python3
"""
Sube (upsert) los rubros_maestros desde json_request/rubros_maestro.json a CosmosDB.

Uso:
    python scripts/migrations/seed_rubros_maestros.py --dry-run
    python scripts/migrations/seed_rubros_maestros.py --execute

Requiere las variables de entorno de Cosmos (o .env):
    COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE, COSMOS_CONTAINER_PARAMETRIZATION
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend_nexa_v2"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    import backend_nexa_v2  # noqa: F401 — registra alias nexa_engine
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "backend_nexa_v2",
        _BACKEND_ROOT / "__init__.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    sys.modules["backend_nexa_v2"] = mod

from nexa_engine.db.container import build_container  # noqa: E402


_RUBROS_JSON = _BACKEND_ROOT / "json_request" / "rubros_maestro.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed rubros_maestros a CosmosDB")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Solo mostrar, no escribir")
    group.add_argument("--execute", action="store_true", help="Escribir en Cosmos")
    args = parser.parse_args()

    rubros: list[dict] = json.loads(_RUBROS_JSON.read_text(encoding="utf-8"))

    print(f"[seed_rubros] {len(rubros)} rubros encontrados en {_RUBROS_JSON.name}")
    for r in rubros:
        r.setdefault("domain", "rubros_maestros")
        r.setdefault("type", "rubro_maestro")
        if not r.get("id"):
            print(f"  ⚠ Rubro sin id: {r}")
            continue
        if args.dry_run:
            print(f"  [dry] upsert id={r['id']} orden={r.get('orden_calculo')}")

    if args.dry_run:
        print("[seed_rubros] Modo dry-run — nada fue escrito.")
        return

    # --- Ejecutar en Cosmos ---
    import os
    # Cargar .env si existe
    _env_file = _BACKEND_ROOT / ".env"
    if _env_file.exists():
        for line in _env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    os.environ["DB_PROVIDER"] = "cosmos"

    container = build_container()
    from nexa_engine.db.ports.document_store import CollectionConfig

    coll = CollectionConfig(name="parameterization", partition_key_field="domain")
    ok = 0
    errors = 0
    for r in rubros:
        if not r.get("id"):
            continue
        try:
            container.parametrization_store.upsert(coll, r)
            print(f"  ✓ upsert id={r['id']}")
            ok += 1
        except Exception as exc:
            print(f"  ✗ ERROR id={r['id']}: {exc}")
            errors += 1

    print(f"\n[seed_rubros] Completado: {ok} ok, {errors} errores.")


if __name__ == "__main__":
    main()
