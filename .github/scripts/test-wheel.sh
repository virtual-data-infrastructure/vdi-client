#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
#
# Shared test script for installing and verifying a vdi wheel.
# Expects EESSI to be initialized (EESSI_EPREFIX set) and wheel
# files to be available in the wheel/ directory.
set -euo pipefail

VDI_LOG_DIR="${VDI_LOG_DIR:-/tmp/vdi-test-logs}"
VDI_VENV="${VDI_VENV:-/tmp/test-vdi}"
WHEEL_DIR="${WHEEL_DIR:-wheel}"

echo "=== Install wheel into venv using EESSI compat-layer Python ==="
EESSI_PYTHON="${EESSI_EPREFIX}/usr/bin/python"
"$EESSI_PYTHON" -m venv "$VDI_VENV"
"$VDI_VENV/bin/pip" install --upgrade pip
"$VDI_VENV/bin/pip" install "$WHEEL_DIR"/*.whl

VDI_BIN="$VDI_VENV/bin/vdi"
mkdir -p "$VDI_LOG_DIR"

echo "=== Test CLI basics ==="
"$VDI_BIN" --version
"$VDI_BIN" --help
"$VDI_BIN" run --dry-run cat /etc/hostname

echo "=== Test run with LD_PRELOAD and log creation ==="
"$VDI_BIN" run cat /etc/hostname
log_count=$(find "$VDI_LOG_DIR" -name '*.log' | wc -l)
if [ "$log_count" -eq 0 ]; then
  echo "Error: no log file was created"
  exit 1
fi
echo "Log file(s) created: $log_count"

echo "=== Test log subcommands ==="
"$VDI_BIN" log list
"$VDI_BIN" log list --long
pid=$(find "$VDI_LOG_DIR" -name 'vdi_log.*.log' -exec basename {} .log \; | head -1 | sed 's/vdi_log\.//')
echo "Showing log for PID: $pid"
"$VDI_BIN" log show "$pid"
