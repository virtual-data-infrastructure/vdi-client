#!/usr/bin/env bash

# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
#
# Portability tests for the libvdi.so wrapper.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Error: libvdi wrapper portability test must run on macOS." >&2
    exit 1
fi

source_file="src/vdi_wrapper/vdi.c"
expected_error="libvdi currently requires Linux"
compiler_output="$(mktemp "${TMPDIR:-/tmp}/libvdi-portability-test.XXXXXX")"
trap 'rm -f "$compiler_output"' EXIT

echo "=== Run libvdi wrapper Linux-only guard test ==="

if cc -fsyntax-only "$source_file" >"$compiler_output" 2>&1; then
    cat "$compiler_output"
    echo "Error: libvdi wrapper compiled on macOS; expected a Linux-only guard failure." >&2
    exit 1
fi

cat "$compiler_output"

if ! grep -qF "$expected_error" "$compiler_output"; then
    echo "Error: compile failure does not explain that libvdi currently requires Linux." >&2
    exit 1
fi

echo "Linux-only guard is reported clearly."
