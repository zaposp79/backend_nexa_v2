#!/bin/bash
# Run functional tests
# Usage: ./run_tests.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

# Activate virtual environment
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "✓ Virtual environment activated (Python $(python --version 2>&1 | awk '{print $2}'))"
fi

# Run from the parent directory so backend_nexa is importable as a package.
python -m backend_nexa.functional_test
