#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"
echo "[INFO] macOS installer scaffold detected."
echo "[INFO] Full macOS dependency/bootstrap logic will be completed in Step 4."
echo "[INFO] For now, run Linux installer only on Linux systems: python3 freetopify.py install"
exit 1
