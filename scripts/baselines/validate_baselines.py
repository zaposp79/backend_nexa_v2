"""
Validate the V2-7 certified baselines.

Runs the regression suite and reports a concise summary. Returns non-zero
exit code if any baseline drift is detected.

Usage:
    cd backend_nexa
    source venv/bin/activate
    python scripts/baselines/validate_baselines.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    print("Validating V2-7 baselines via tests/baselines/...\n")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/baselines", "--tb=short", "-v"],
        cwd=BACKEND_ROOT,
        check=False,
    )
    if proc.returncode == 0:
        print("\n[OK] All baselines validated — no drift detected.")
    else:
        print("\n[FAIL] Baseline drift detected. See pytest output above.")
        print("Either revert the change, or re-certify by running:")
        print("  python scripts/baselines/generate_baselines.py")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
