#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
#
# AddressSanitizer tests for the libvdi.so wrapper.
#
set -euo pipefail

if [ -z "${EESSI_EPREFIX:-}" ]; then
  echo "Error: EESSI_EPREFIX is not set; initialize EESSI before running this test."
  exit 1
fi

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

echo "=== Build ASan-instrumented wrapper ==="
make clean
make asan

TEST_ROOT=$(mktemp -d)
HTTP_PID=""

cleanup() {
  if [ -n "$HTTP_PID" ]; then
    kill "$HTTP_PID" 2>/dev/null || true
  fi
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

run_download_return_path_test() {
  # This test focuses on the returned download path by:
  # - VDI_DOWNLOAD_BASE is unset, so download_base is heap-allocated.
  # - The URL has no filename, so local_filename is heap-allocated.
  # - LeakSanitizer is disabled, while ASan memory-error checks remain enabled.
  mkdir -p "$TEST_ROOT/download-return-path/logs"

  cat >"$TEST_ROOT/download-return-path/server.py" <<'EOF'
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello from vdi\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
EOF

  python3 "$TEST_ROOT/download-return-path/server.py" \
    >"$TEST_ROOT/download-return-path/http.log" 2>&1 &
  HTTP_PID=$!

  for _ in $(seq 1 30); do
    if python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/", timeout=1).read(1)' >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done

  if ! python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/", timeout=1).read(1)' >/dev/null 2>&1; then
    echo "Error: download return-path test HTTP server did not become ready."
    cat "$TEST_ROOT/download-return-path/http.log"
    return 1
  fi

  cat >"$TEST_ROOT/download-return-path/test.c" <<'EOF'
#include <stdio.h>


int main(void) {
    FILE *file = fopen("http://127.0.0.1:8000/", "r");
    if (file == NULL) {
        return 1;
    }

    char buffer[256] = {0};
    fread(buffer, 1, sizeof(buffer) - 1, file);
    fclose(file);

    printf("%s", buffer);
    return 0;
}
EOF

  gcc -fsanitize=address -g -O0 \
    -o "$TEST_ROOT/download-return-path/test" \
    "$TEST_ROOT/download-return-path/test.c"

  ASAN_RUNTIME=$(gcc -print-file-name=libasan.so)
  if [ ! -f "$ASAN_RUNTIME" ]; then
    ASAN_RUNTIME=$(ldconfig -p | awk '/libasan\.so/ {print $NF; exit}')
  fi

  echo "=== Run download return-path ASan test ==="
  unset VDI_DOWNLOAD_BASE

  LD_PRELOAD="$ASAN_RUNTIME:$PWD/src/vdi_wrapper/build/libvdi-asan.so" \
  ASAN_OPTIONS=detect_stack_use_after_return=1:detect_leaks=0 \
  VDI_LOG_DIR="$TEST_ROOT/download-return-path/logs" \
  "$TEST_ROOT/download-return-path/test" >"$TEST_ROOT/download-return-path/test-output.txt"

  cat "$TEST_ROOT/download-return-path/test-output.txt"

  if [ "$(cat "$TEST_ROOT/download-return-path/test-output.txt")" != "hello from vdi" ]; then
    echo "Error: unexpected download return-path test output."
    return 1
  fi

  if [ "$(find "$TEST_ROOT/download-return-path/logs" -type f -name '*.log' | wc -l)" -eq 0 ]; then
    echo "Error: no download return-path log file was created."
    return 1
  fi

  kill "$HTTP_PID" 2>/dev/null || true
  HTTP_PID=""
}

run_download_return_path_test

echo "libvdi wrapper ASan tests passed."
