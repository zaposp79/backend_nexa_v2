#!/usr/bin/env python3
"""Seed: cargar la parametrización local (storage/parametrization) en Cosmos DB.

Apunta al esquema CANÓNICO de Cosmos definido por
``CosmosParametrizationRepository``:

  Database:      nexa_pricing_db         (COSMOS_DATABASE)
  Container:     parametrization         (COSMOS_CONTAINER_PARAMETRIZATION)
  Partition key: /domain

Documentos generados por dominio (gn, hr, op):

  type=parametrization_version  — uno por versión
      id          = version_id            (p.ej. "v2-7")
      pk / domain = "<dominio>"
      payload     = JSON completo del dominio (storage/parametrization/v2-7/<dominio>.json)
      status      = "active" | "inactive"
      created_at, source, file_name, hash, sheet_count, total_rows

  type=active_version            — puntero a la versión activa del dominio
      id          = "active_<dominio>"
      pk / domain = "<dominio>"
      active_version = version_id

Fuente de datos (estado actual del repo):
  - Metadatos: storage/parametrization/<dominio>/versions.json
        gn/hr/op  -> lista [{version_id, is_active, ...}]
  - Payload de la versión activa: storage/parametrization/v2-7/<dominio>.json
    (también se aceptan overrides "path" o <dominio>/<version_id>.json).

Solo se siembra la versión ACTIVA de cada dominio, porque es la única cuyo
payload existe localmente como archivo. Las versiones históricas del índice
solo tienen metadatos, no payload, y se omiten (se informa cuáles).

Uso:
  # 1) Provisionar DB + container (idempotente) y sembrar:
  python scripts/migrations/seed_cosmos_parametrization.py --provision --execute

  # 2) Solo previsualizar lo que se escribiría:
  python scripts/migrations/seed_cosmos_parametrization.py --dry-run

  # 3) Sembrar (DB/container ya existen):
  python scripts/migrations/seed_cosmos_parametrization.py --execute

  # 4) Verificar lo que quedó en Cosmos:
  python scripts/migrations/seed_cosmos_parametrization.py --verify

  # Acotar a dominios concretos:
  python scripts/migrations/seed_cosmos_parametrization.py --execute --domains gn hr

Variables de entorno requeridas (se leen de os.environ o de un .env si está
python-dotenv instalado):
  COSMOS_ENDPOINT   https://<cuenta>.documents.azure.com:443/
  COSMOS_KEY        <primary o secondary key>
  COSMOS_DATABASE   nexa_pricing_db      (default si vacío)
  COSMOS_CONTAINER_PARAMETRIZATION  parametrization   (default si vacío)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Registrar el alias de paquete `nexa_engine` --------------------------
# El proyecto se importa como `backend_nexa` y registra el alias `nexa_engine`
# (ver backend_nexa/__init__.py). Para correr este script de forma autónoma
# añadimos el directorio padre de backend_nexa/ al sys.path.
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parents[2]            # .../backend_nexa
_PROJECT_PARENT = PROJECT_ROOT.parent      # .../code
if str(_PROJECT_PARENT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_PARENT))


def _load_dotenv_early() -> None:
    """Carga backend_nexa/.env ANTES de importar nexa_engine.

    Es crítico: ``storage_constants`` congela ``COSMOS_DATABASE_NAME`` y
    ``COSMOS_CONTAINER_NAME`` en tiempo de import (os.getenv una sola vez).
    Si el .env no está cargado antes de ese import, el repositorio Cosmos se
    conectaría a la base/container por defecto y no a los valores del .env.

    No sobrescribe variables ya presentes en el entorno (override=False).
    """
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore[import]
        load_dotenv(env_path)  # override=False por defecto
        return
    except ImportError:
        pass
    # Fallback mínimo si python-dotenv no está instalado.
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv_early()

import backend_nexa  # noqa: E402,F401  — registra el alias nexa_engine

from nexa_engine.modules.parametrizacion.shared.models.version_summary import (  # noqa: E402
    VersionSummary,
)
from nexa_engine.modules.parametrizacion.shared.constants.storage_constants import (  # noqa: E402
    VALID_DOMAINS,
    COSMOS_DATABASE_DEFAULT,
    COSMOS_CONTAINER_DEFAULT,
    COSMOS_PARTITION_KEY,
)

PARAMETRIZATION_DIR = PROJECT_ROOT / "storage" / "parametrization"
V27_DIR = PARAMETRIZATION_DIR / "v2-7"


# ---------------------------------------------------------------------------
# Carga de metadatos + payload desde los archivos locales
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _active_entry(domain: str) -> Optional[dict]:
    """Devuelve la entrada de la versión activa del índice del dominio."""
    versions_path = PARAMETRIZATION_DIR / domain / "versions.json"
    if not versions_path.exists():
        return None
    raw = _read_json(versions_path)

    if isinstance(raw, list):  # gn / hr / op
        for entry in raw:
            if entry.get("is_active"):
                return {**entry, "version_id": entry["version_id"]}
        return None

    return None


def _resolve_payload_path(domain: str, entry: dict) -> Optional[Path]:
    """Resuelve el archivo de payload de la versión activa.

    Orden: override `path` -> <dominio>/<version_id>.json -> v2-7/<dominio>.json.
    """
    domain_dir = PARAMETRIZATION_DIR / domain
    version_id = entry["version_id"]

    if entry.get("path"):
        candidate = (domain_dir / entry["path"]).resolve()
        if candidate.exists():
            return candidate

    candidate = domain_dir / f"{version_id}.json"
    if candidate.exists():
        return candidate

    candidate = V27_DIR / f"{domain}.json"
    if candidate.exists():
        return candidate

    return None


def load_domain(domain: str) -> Tuple[VersionSummary, Dict[str, Any]]:
    """Construye (summary, payload) de la versión activa de un dominio."""
    entry = _active_entry(domain)
    if entry is None:
        raise FileNotFoundError(
            f"[{domain}] no hay versión activa en {domain}/versions.json"
        )

    payload_path = _resolve_payload_path(domain, entry)
    if payload_path is None:
        raise FileNotFoundError(
            f"[{domain}] no se encontró archivo de payload para version_id="
            f"{entry['version_id']!r} (busqué path override, {domain}/<id>.json "
            f"y v2-7/{domain}.json)"
        )

    payload_text = payload_path.read_text(encoding="utf-8")
    payload = json.loads(payload_text)

    summary = VersionSummary(
        version_id=entry["version_id"],
        filename=entry.get("filename") or entry.get("label") or f"{domain}-{entry['version_id']}",
        uploaded_at=entry.get("uploaded_at") or entry.get("timestamp") or "",
        is_active=True,
        sheet_count=entry.get("sheet_count", 0),
        total_rows=entry.get("total_rows", 0),
    )
    return summary, payload


def list_skipped_versions(domain: str) -> List[str]:
    """Versiones del índice que NO se siembran (no tienen payload local)."""
    versions_path = PARAMETRIZATION_DIR / domain / "versions.json"
    if not versions_path.exists():
        return []
    raw = _read_json(versions_path)
    skipped: List[str] = []
    if isinstance(raw, list):  # gn / hr / op
        for entry in raw:
            if not entry.get("is_active"):
                skipped.append(str(entry.get("version_id")))
    return skipped


# ---------------------------------------------------------------------------
# Entorno / conexión Cosmos
# ---------------------------------------------------------------------------

def _cosmos_settings() -> Tuple[str, str, str, str]:
    endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
    key = os.getenv("COSMOS_KEY", "").strip()
    database = os.getenv("COSMOS_DATABASE", "").strip() or COSMOS_DATABASE_DEFAULT
    container = os.getenv("COSMOS_CONTAINER_PARAMETRIZATION", "").strip() or COSMOS_CONTAINER_DEFAULT
    print(f"[cosmos] endpoint={endpoint}  database={database}  container={container}")
    if not endpoint or not key:
        print(
            "ERROR: faltan COSMOS_ENDPOINT y/o COSMOS_KEY en el entorno.\n"
            "       Configúralos en variables de entorno o en backend_nexa/.env",
            file=sys.stderr,
        )
        sys.exit(2)
    return endpoint, key, database, container


def provision(endpoint: str, key: str, database: str, container: str) -> None:
    """Crea la base y el container con partition key /domain (idempotente)."""
    from azure.cosmos import CosmosClient, PartitionKey  # type: ignore[import]

    client = CosmosClient(endpoint, credential=key)
    db = client.create_database_if_not_exists(id=database)
    db.create_container_if_not_exists(
        id=container,
        partition_key=PartitionKey(path=COSMOS_PARTITION_KEY),
    )
    print(f"[provision] OK  database={database}  container={container}  pk={COSMOS_PARTITION_KEY}")


# ---------------------------------------------------------------------------
# Operaciones principales
# ---------------------------------------------------------------------------

def cmd_dry_run(domains: List[str]) -> int:
    print("\n=== SEED Cosmos parametrización [DRY-RUN] ===\n")
    ok = True
    for domain in domains:
        try:
            summary, payload = load_domain(domain)
        except FileNotFoundError as exc:
            print(f"  SKIP {exc}")
            ok = False
            continue
        size_kb = len(json.dumps(payload, ensure_ascii=False)) / 1024
        skipped = list_skipped_versions(domain)
        print(f"[{domain}]")
        print(f"  version_id activo : {summary.version_id}")
        print(f"  filename          : {summary.filename}")
        print(f"  payload (~KB)     : {size_kb:.1f}")
        print(f"  -> doc id={summary.version_id} (type=parametrization_version, pk={domain})")
        print(f"  -> doc id=active_{domain} (type=active_version)")
        if skipped:
            print(f"  versiones omitidas (sin payload local): {', '.join(skipped)}")
        print()
    print("DRY-RUN: no se escribió nada en Cosmos.")
    return 0 if ok else 1


def cmd_execute(domains: List[str], endpoint: str, key: str) -> int:
    from nexa_engine.modules.parametrizacion.shared.repositories.cosmos_parametrization_repository import (
        CosmosParametrizationRepository,
    )

    print("\n=== SEED Cosmos parametrización [EXECUTE] ===\n")
    repo = CosmosParametrizationRepository(endpoint=endpoint, key=key)
    ok = True
    for domain in domains:
        try:
            summary, payload = load_domain(domain)
        except FileNotFoundError as exc:
            print(f"  SKIP {exc}")
            ok = False
            continue
        version_id = repo.save_version(domain, summary, payload)
        print(f"[{domain}] guardado version_id={version_id} y activado (active_{domain}).")
    print("\nEXECUTE: completado." if ok else "\nEXECUTE: completado con omisiones.")
    return 0 if ok else 1


def cmd_verify(domains: List[str], endpoint: str, key: str) -> int:
    from nexa_engine.modules.parametrizacion.shared.repositories.cosmos_parametrization_repository import (
        CosmosParametrizationRepository,
    )

    print("\n=== VERIFY Cosmos parametrización ===\n")
    repo = CosmosParametrizationRepository(endpoint=endpoint, key=key)
    ok = True
    for domain in domains:
        summary = repo.get_active_summary(domain)
        if summary is None:
            print(f"[{domain}] NO hay versión activa en Cosmos.")
            ok = False
            continue
        payload = repo.get_active_payload(domain) or {}
        payload_keys = list(payload.keys()) if isinstance(payload, dict) else "(lista)"
        print(f"[{domain}] activo={summary.version_id}  claves_payload={payload_keys}")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sembrar parametrización local en Cosmos DB (esquema canónico)."
    )
    parser.add_argument("--provision", action="store_true",
                        help="Crear DB + container (partition key /domain) si no existen.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Previsualizar; no escribe.")
    mode.add_argument("--execute", action="store_true", help="Escribir en Cosmos.")
    mode.add_argument("--verify", action="store_true", help="Leer de Cosmos y validar.")
    parser.add_argument("--domains", nargs="+", default=list(VALID_DOMAINS),
                        help=f"Dominios a procesar (default: {' '.join(VALID_DOMAINS)}).")
    args = parser.parse_args()

    domains = [d for d in args.domains if d in VALID_DOMAINS]
    invalid = [d for d in args.domains if d not in VALID_DOMAINS]
    if invalid:
        print(f"ERROR: dominios inválidos {invalid}. Válidos: {VALID_DOMAINS}", file=sys.stderr)
        sys.exit(2)

    # dry-run no necesita conexión.
    if args.dry_run or (not args.execute and not args.verify and not args.provision):
        sys.exit(cmd_dry_run(domains))

    # El .env ya se cargó al inicio (ver _load_dotenv_early), antes de importar
    # nexa_engine, para que COSMOS_DATABASE/CONTAINER del .env tengan efecto.
    endpoint, key, database, container = _cosmos_settings()

    if args.provision:
        provision(endpoint, key, database, container)

    if args.execute:
        sys.exit(cmd_execute(domains, endpoint, key))
    if args.verify:
        sys.exit(cmd_verify(domains, endpoint, key))

    # Solo --provision: nada más que hacer.
    sys.exit(0)


if __name__ == "__main__":
    main()
