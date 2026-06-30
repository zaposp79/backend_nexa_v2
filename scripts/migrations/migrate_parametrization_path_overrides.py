#!/usr/bin/env python3
"""Migration: eliminate path overrides from parametrization versions.json.

Current state (FASE DB.5):
  All active parametrization versions use path overrides like ../v2-7/hr.json.
  These bypass DocumentStore and use read_json() directly, preventing full
  DocumentStore convergence.

  versions.json entry with path override:
    {"version_id": "v2-7", "is_active": true, "path": "../v2-7/hr.json", ...}

  versions.json entry without path override (after migration):
    {"version_id": "v2-7", "is_active": true, ...}  (path key removed)
  And the data file is available at:
    storage/parametrization/hr/v2-7.json  (same content, readable by DocumentStore)

Migration steps per domain:
  1. Read the source file (path override target, e.g. storage/parametrization/v2-7/hr.json).
  2. Compute SHA-256 of source.
  3. Create destination file at storage/parametrization/{domain}/{version_id}.json.
     The destination already exists if DocumentStore has written it; if so, verify hash.
  4. Remove the "path" key from the versions.json entry.
  5. Verify hash of written file matches source.

Idempotence:
  - If destination exists and hash matches: skip (already migrated).
  - If destination exists and hash differs: ABORT and report.
  - If destination does not exist: copy source → destination.

Usage:
  python scripts/migrations/migrate_parametrization_path_overrides.py --dry-run
  python scripts/migrations/migrate_parametrization_path_overrides.py --execute
  python scripts/migrations/migrate_parametrization_path_overrides.py --report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARAMETRIZATION_DIR = PROJECT_ROOT / "storage" / "parametrization"

DOMAINS = ["hr", "gn", "op"]

DOMAIN_VERSIONS_FORMAT = "list"          # [{version_id, is_active, ...}, ...]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_versions_list(domain: str) -> list[dict]:
    p = PARAMETRIZATION_DIR / domain / "versions.json"
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def _load_versions_dict(domain: str) -> dict:
    p = PARAMETRIZATION_DIR / domain / "versions.json"
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _find_path_overrides(domain: str) -> list[dict]:
    """Return entries with a path override for the given domain."""
    overrides = []
    for entry in _load_versions_list(domain):
        if entry.get("path"):
            overrides.append(entry)
    return overrides


def _resolve_override_path(domain: str, entry: dict) -> Path:
    domain_dir = PARAMETRIZATION_DIR / domain
    return (domain_dir / entry["path"]).resolve()


def _destination_path(domain: str, version_id: str) -> Path:
    return PARAMETRIZATION_DIR / domain / f"{version_id}.json"


def report() -> None:
    print("\n=== Path Override Report ===\n")
    total = 0
    for domain in DOMAINS:
        overrides = _find_path_overrides(domain)
        for entry in overrides:
            total += 1
            version_id = entry.get("id") or entry.get("version_id", "?")
            src = _resolve_override_path(domain, entry)
            dst = _destination_path(domain, version_id)
            src_hash = sha256(src) if src.exists() else "MISSING"
            dst_exists = dst.exists()
            dst_hash = sha256(dst) if dst_exists else "-"
            hash_match = (src_hash == dst_hash) if dst_exists else "-"
            print(f"Domain:     {domain}")
            print(f"Version:    {version_id}")
            print(f"Override:   {entry['path']}")
            print(f"Source:     {src}  ({'exists' if src.exists() else 'MISSING'})")
            print(f"Dest:       {dst}  ({'exists' if dst_exists else 'missing'})")
            print(f"Src hash:   {src_hash[:16]}...")
            print(f"Dst hash:   {dst_hash[:16] if len(dst_hash) > 16 else dst_hash}...")
            print(f"Hash match: {hash_match}")
            print()
    if total == 0:
        print("No path overrides found — already fully migrated or no data.")
    else:
        print(f"Total path overrides: {total}")


def migrate(dry_run: bool = True) -> bool:
    mode = "DRY-RUN" if dry_run else "EXECUTE"
    print(f"\n=== Path Override Migration [{mode}] ===\n")
    success = True

    for domain in DOMAINS:
        overrides = _find_path_overrides(domain)
        for entry in overrides:
            version_id = entry.get("id") or entry.get("version_id", "?")
            src = _resolve_override_path(domain, entry)
            dst = _destination_path(domain, version_id)

            print(f"[{domain}/{version_id}]")

            if not src.exists():
                print(f"  ERROR: source file not found: {src}")
                success = False
                continue

            src_hash = sha256(src)
            print(f"  source hash: {src_hash[:16]}...")

            if dst.exists():
                dst_hash = sha256(dst)
                if src_hash == dst_hash:
                    print("  destination exists with matching hash — SKIP (idempotent)")
                    if not dry_run:
                        _remove_path_key(domain, version_id)
                        print("  versions.json path key removed")
                    continue
                else:
                    print(f"  ERROR: destination exists with DIFFERENT hash!")
                    print(f"    src: {src_hash[:16]}...")
                    print(f"    dst: {dst_hash[:16]}...")
                    print("  ABORTING this entry — manual review required.")
                    success = False
                    continue

            # Destination does not exist — copy
            if dry_run:
                print(f"  [DRY-RUN] would copy → {dst}")
                print(f"  [DRY-RUN] would remove 'path' key from versions.json")
            else:
                shutil.copy2(src, dst)
                written_hash = sha256(dst)
                if written_hash != src_hash:
                    print("  ERROR: written file hash mismatch — rollback!")
                    dst.unlink()
                    success = False
                    continue
                print(f"  copied → {dst}")
                _remove_path_key(domain, version_id)
                print("  versions.json path key removed")

            print()

    return success


def _remove_path_key(domain: str, version_id: str) -> None:
    """Remove the 'path' key from the versions.json entry for the given version."""
    versions_path = PARAMETRIZATION_DIR / domain / "versions.json"
    raw = json.loads(versions_path.read_text(encoding="utf-8"))

    if isinstance(raw, list):
        for entry in raw:
            if entry.get("version_id") == version_id:
                entry.pop("path", None)
        versions_path.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    elif isinstance(raw, dict):
        for entry in raw.get("versions", []):
            if entry.get("id") == version_id:
                entry.pop("path", None)
        versions_path.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate parametrization path overrides to DocumentStore-compatible paths."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Show what would be done, no writes.")
    group.add_argument("--execute", action="store_true", help="Actually perform the migration.")
    group.add_argument("--report", action="store_true", help="Report current state only.")
    args = parser.parse_args()

    if args.report:
        report()
    elif args.dry_run:
        ok = migrate(dry_run=True)
        sys.exit(0 if ok else 1)
    elif args.execute:
        ok = migrate(dry_run=False)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
