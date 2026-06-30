"""
Recompute SHA-256 hashes of v2-7 parametrization files and print them.

Useful when you intentionally update parametrization and need to refresh
the baseline manifest. Does NOT modify any file — only reports.

Usage:
    cd backend_nexa
    source venv/bin/activate
    python scripts/baselines/recompute_hashes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
REPO_ROOT    = BACKEND_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

from scripts.baselines.generate_baselines import compute_param_hashes


def main() -> int:
    hashes = compute_param_hashes()
    print("Current parametrization SHA-256 hashes (canonicalized JSON):")
    for k, v in hashes.items():
        print(f"  {k:<20s} {v}")
    print("\nTo refresh the manifest with these hashes, run:")
    print("  python scripts/baselines/generate_baselines.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
