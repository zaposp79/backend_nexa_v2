#!/usr/bin/env python3
"""Compare pytest failed node ids between a baseline and a Python 3.14 gate.

Usage:
    python scripts/compare_pytest_nodeids.py baseline.txt reports/python314/full-gate.txt

The script is intentionally text-based so it can compare captured pytest output
from local runs, CI logs, or archived artifacts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NODE_ID_PATTERN = re.compile(
    r"(?P<nodeid>(?:tests|contracts)/[^\s:]+\.py::[^\s]+)"
)


def extract_nodeids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {match.group("nodeid").rstrip(",") for match in NODE_ID_PATTERN.finditer(text)}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: python scripts/compare_pytest_nodeids.py "
            "<baseline-output.txt> <candidate-output.txt>",
            file=sys.stderr,
        )
        return 2

    baseline_path = Path(argv[1])
    candidate_path = Path(argv[2])
    baseline = extract_nodeids(baseline_path)
    candidate = extract_nodeids(candidate_path)

    new_failures = sorted(candidate - baseline)
    resolved_failures = sorted(baseline - candidate)

    print(f"baseline_failures={len(baseline)}")
    print(f"candidate_failures={len(candidate)}")
    print(f"new_failures={len(new_failures)}")
    for nodeid in new_failures:
        print(f"NEW {nodeid}")
    print(f"resolved_failures={len(resolved_failures)}")
    for nodeid in resolved_failures:
        print(f"RESOLVED {nodeid}")

    return 1 if new_failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
