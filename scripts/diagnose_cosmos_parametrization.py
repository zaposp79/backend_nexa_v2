"""Diagnostico del container de parametrizacion en Cosmos DB.

Muestra que documentos hay en el container `COSMOS_CONTAINER_PARAMETRIZATION`
(default: `parameterization`), clasificados por dominio (hr, gn, op).

Uso:
    python scripts/diagnose_cosmos_parametrization.py

Requiere en .env o variables de entorno:
    DB_PROVIDER=cosmos
    COSMOS_ENDPOINT=...
    COSMOS_KEY=...
    COSMOS_DATABASE=...
    COSMOS_CONTAINER_PARAMETRIZATION=parameterization
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# El paquete es backend_nexa_v2; su padre debe estar en sys.path para importarlo.
# Al importar el paquete, __init__.py registra el alias nexa_engine en sys.modules.
_REPO_ROOT = Path(__file__).resolve().parent.parent          # c:\Nexa\code\backend_nexa_v2
_PARENT = _REPO_ROOT.parent                                  # c:\Nexa\code
sys.path.insert(0, str(_PARENT))
sys.path.insert(0, str(_REPO_ROOT))
# Importar el paquete para activar el alias nexa_engine
import importlib as _importlib
_pkg_name = _REPO_ROOT.name  # "backend_nexa_v2"
try:
    _importlib.import_module(_pkg_name)
except Exception:
    pass

# Cargar .env si existe
_env_file = _REPO_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def _hr(s: int) -> str:
    kb = s / 1024
    return f"{kb:.1f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"


def _test_fallback_query(store, domain: str, collection) -> bool:
    """Prueba la query de fallback que usa el motor cuando no hay indice 'versions'."""
    try:
        docs, _ = store.query(collection, {"domain": domain, "status": "active"})
        if docs:
            payload = docs[0].get("payload")
            if isinstance(payload, dict) and payload:
                return True
        return False
    except Exception as exc:
        print(f"    [ERROR] fallback query fallo: {exc}")
        return False


def main() -> None:
    from nexa_engine.db.config import load_config
    from nexa_engine.db.factory import build_parametrization_document_store
    from nexa_engine.db.models.collection_config import CollectionConfig

    cfg = load_config()
    print(f"\n{'='*60}")
    print(f"  DIAGNOSTICO COSMOS -- container de parametrizacion")
    print(f"{'='*60}")
    print(f"  DB_PROVIDER      : {cfg.provider}")
    if cfg.cosmos:
        print(f"  COSMOS_ENDPOINT  : {cfg.cosmos.endpoint}")
        print(f"  COSMOS_DATABASE  : {cfg.cosmos.database}")
        print(f"  COSMOS_CONTAINER : {cfg.cosmos.container_parametrization!r}")
    print()

    if cfg.provider != "cosmos":
        print("[WARN]  DB_PROVIDER != cosmos -- no se puede consultar Cosmos.")
        print("   Establece DB_PROVIDER=cosmos en .env y reintenta.")
        return

    store = build_parametrization_document_store(cfg)
    print("[OK]  Conexion a CosmosDocumentStore establecida\n")

    # Listar TODOS los documentos (cross-partition)
    sentinel = CollectionConfig(name="parametrization_diagnostics")
    try:
        all_docs, _ = store.query(sentinel, {})
    except Exception as exc:
        print(f"[FALTA]  Error al consultar Cosmos: {exc}")
        return

    if not all_docs:
        print("[WARN]  El container esta VACIO -- no hay ningun documento.")
        print()
        print("   -> Sube los archivos Excel via los endpoints:")
        print("     POST /api/v1/parametrization/hr/upload")
        print("     POST /api/v1/parametrization/gn/upload")
        print("     POST /api/v1/parametrization/op/upload")
        return

    print(f"Total documentos encontrados: {len(all_docs)}\n")

    # Clasificar por dominio
    by_domain: dict[str, list[dict]] = {}
    for doc in all_docs:
        domain = doc.get("domain") or doc.get("payload", {}).get("domain") or "desconocido"
        by_domain.setdefault(domain, []).append(doc)

    for domain in sorted(by_domain.keys()):
        docs = by_domain[domain]
        print(f"  DOMINIO: {domain.upper()!r}  ({len(docs)} documento(s))")
        print(f"  {'-'*54}")
        for doc in docs:
            doc_id = doc.get("id", "?")
            status = doc.get("status") or doc.get("payload", {}).get("status") or "?"
            doc_type = doc.get("type") or doc.get("payload", {}).get("type") or "?"
            created = doc.get("created_at") or doc.get("payload", {}).get("created_at") or "?"
            filename = doc.get("file_name") or doc.get("payload", {}).get("file_name") or "?"
            payload = doc.get("payload")
            payload_size = len(json.dumps(payload)) if payload else 0
            print(f"    id       : {doc_id}")
            print(f"    type     : {doc_type}")
            print(f"    status   : {status}")
            print(f"    file     : {filename}")
            print(f"    created  : {created}")
            print(f"    payload  : {_hr(payload_size) if payload_size else 'vacio'}")
            # Verificar integridad del payload
            if payload is None:
                print(f"    [WARN]  SIN payload -- documento no valido para el motor")
            elif not isinstance(payload, dict):
                print(f"    [WARN]  payload no es dict (tipo={type(payload).__name__})")
            else:
                keys_preview = list(payload.keys())[:8]
                extra = "..." if len(payload) > 8 else ""
                print(f"    keys     : {keys_preview}{extra}")
            print()
        print()

    # Resumen de versiones activas por dominio HR/GN/OP
    print(f"{'='*60}")
    print("  RESUMEN -- versiones activas por dominio")
    print(f"{'='*60}")
    for domain in ("hr", "gn", "op"):
        docs = by_domain.get(domain, [])
        active = [d for d in docs if (
            d.get("status") == "active" or
            d.get("payload", {}).get("status") == "active"
        ) and d.get("id") != "versions"]
        index = [d for d in docs if d.get("id") == "versions"]
        versions_doc_status = "[OK] presente" if index else "[FALTA] ausente"
        if active:
            print(f"  {domain.upper()}: [OK] {len(active)} version(es) activa(s) | indice 'versions': {versions_doc_status}")
            for a in active:
                doc_id = a.get("id", "?")
                fname = a.get("file_name") or a.get("payload", {}).get("file_name") or "?"
                print(f"       -> id={doc_id}  file={fname}")
        else:
            print(f"  {domain.upper()}: [FALTA] SIN version activa | indice 'versions': {versions_doc_status}")
    print()

    # Probar queries de fallback (las que usa el motor cuando falta el indice 'versions')
    print(f"{'='*60}")
    print("  PRUEBA QUERIES DE FALLBACK (ruta que usa el motor)")
    print(f"{'='*60}")
    print("  (Estas queries se ejecutan cuando el indice 'versions' no existe en Cosmos)")
    print()

    _domain_collections = {
        "hr": "hr",
        "gn": "gn",
        "op": "op",
    }
    fallback_ok = True
    for domain, coll_name in _domain_collections.items():
        collection = CollectionConfig(name=coll_name)
        ok = _test_fallback_query(store, domain, collection)
        status_str = "[OK]  retorna payload activo" if ok else "[FALTA]  NO retorna datos -- el motor fallara"
        print(f"  {domain.upper()}: {status_str}")
        if not ok:
            fallback_ok = False
    print()

    # Diagnostico final
    problems = []
    for domain in ("hr", "gn", "op"):
        docs = by_domain.get(domain, [])
        active = [d for d in docs if (
            d.get("status") == "active" or
            d.get("payload", {}).get("status") == "active"
        ) and d.get("id") != "versions"]
        if not active:
            problems.append(f"  * No hay version activa para {domain.upper()}")
        else:
            for a in active:
                if not a.get("payload"):
                    problems.append(f"  * {domain.upper()} id={a.get('id')}: payload vacio")

    if not fallback_ok:
        problems.append("  * Una o mas queries de fallback fallaron (ver detalle arriba)")

    if problems:
        print("[WARN]  PROBLEMAS DETECTADOS:")
        for p in problems:
            print(p)
        print()
        print("  -> Para poblar el container, sube los archivos Excel:")
        print("    POST /api/v1/parametrization/hr/upload")
        print("    POST /api/v1/parametrization/gn/upload")
        print("    POST /api/v1/parametrization/op/upload")
        print()
        print("  -> Si las queries de fallback fallan pero hay datos, puede ser un problema")
        print("     de partition key. Verifica que el container usa partition key /domain")
        print("     o re-sube los archivos Excel para regenerar el indice 'versions'.")
    else:
        print("[OK]  Container OK -- HR, GN y OP tienen version activa con payload.")
        print("[OK]  Queries de fallback funcionan -- el motor puede leer parametrizacion.")
    print()


if __name__ == "__main__":
    main()
