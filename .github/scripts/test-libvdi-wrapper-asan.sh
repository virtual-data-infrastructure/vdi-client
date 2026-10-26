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

start_http_server() {
  local server_dir=$1
  local port=$2

  mkdir -p "$server_dir"

  cat >"$server_dir/server.py" <<'EOF'
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys


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


HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
EOF

  python3 "$server_dir/server.py" "$port" \
    >"$server_dir/http.log" 2>&1 &
  HTTP_PID=$!
}

wait_for_http_server() {
  local port=$1
  local server_dir=$2

  for _ in $(seq 1 30); do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$port/', timeout=1).read(1)" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done

  echo "Error: HTTP server on port $port did not become ready."
  cat "$server_dir/http.log"
  return 1
}

stop_http_server() {
  if [ -n "$HTTP_PID" ]; then
    kill "$HTTP_PID" 2>/dev/null || true
    HTTP_PID=""
  fi
}

cleanup() {
  stop_http_server
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

run_open_access_flags_mapping_test() {
  local test_dir="$TEST_ROOT/open-access-flags-mapping"
  local detect_leaks=1

  if [ "$(uname -m)" = "riscv64" ]; then
    detect_leaks=0
  fi

  mkdir -p "$test_dir"

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct flags_case {
    int flags;
    const char *expected;
};

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }

    void *wrapper = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (wrapper == NULL) {
        fprintf(stderr, "Error: dlopen() failed: %s\n", dlerror());
        return 2;
    }

    char *(*map_flags_to_strings)(int) = dlsym(wrapper, "map_flags_to_strings");
    if (map_flags_to_strings == NULL) {
        fprintf(stderr, "Error: map_flags_to_strings() is unavailable: %s\n", dlerror());
        dlclose(wrapper);
        return 2;
    }

    struct flags_case cases[] = {
        {O_RDONLY, "O_RDONLY"},
        {O_WRONLY, "O_WRONLY"},
        {O_RDWR, "O_RDWR"},
        {O_WRONLY | O_CREAT, "O_WRONLY+O_CREAT"},
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        char *mapped = map_flags_to_strings(cases[i].flags);
        if (mapped == NULL) {
            fprintf(stderr, "Error: map_flags_to_strings() returned NULL.\n");
            dlclose(wrapper);
            return 1;
        }

        int matches = strcmp(mapped, cases[i].expected) == 0;
        if (!matches) {
            fprintf(
                stderr,
                "Error: flags %d mapped to '%s'; expected '%s'.\n",
                cases[i].flags,
                mapped,
                cases[i].expected
            );
        }

        free(mapped);
        if (!matches) {
            dlclose(wrapper);
            return 1;
        }
    }

    dlclose(wrapper);
    return 0;
}
EOF

  gcc -fsanitize=address -g -O0 \
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -ldl

  echo "=== Run open access flags mapping ASan test ==="
  if ! ASAN_OPTIONS=detect_stack_use_after_return=1:detect_leaks=$detect_leaks \
    "$test_dir/test" "$PWD/src/vdi_wrapper/build/libvdi-asan.so"; then
    echo "Error: open access flags mapping test failed."
    return 1
  fi
}

run_shell_variable_expansion_bounds_test() {
  local test_dir="$TEST_ROOT/shell-variable-expansion-bounds"
  local detect_leaks=1

  if [ "$(uname -m)" = "riscv64" ]; then
    detect_leaks=0
  fi

  mkdir -p "$test_dir"

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPANSION_BUFFER_SIZE 4096
#define LONG_VALUE_SIZE (EXPANSION_BUFFER_SIZE * 2)

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }

    void *wrapper = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (wrapper == NULL) {
        fprintf(stderr, "Error: dlopen() failed: %s\n", dlerror());
        return 2;
    }

    char *(*expand_shell_vars)(const char *) = dlsym(wrapper, "expand_shell_vars");
    if (expand_shell_vars == NULL) {
        fprintf(stderr, "Error: expand_shell_vars() is unavailable: %s\n", dlerror());
        dlclose(wrapper);
        return 2;
    }

    char *long_value = calloc(LONG_VALUE_SIZE + 1, 1);
    if (long_value == NULL) {
        dlclose(wrapper);
        return 2;
    }
    memset(long_value, 'x', LONG_VALUE_SIZE);

    if (setenv("VDI_TEST_LONG_VALUE", long_value, 1) != 0) {
        free(long_value);
        dlclose(wrapper);
        return 2;
    }

    char *expanded = expand_shell_vars("$VDI_TEST_LONG_VALUE");
    free(long_value);

    if (expanded == NULL) {
        fprintf(stderr, "Error: expand_shell_vars() returned NULL.\n");
        dlclose(wrapper);
        return 1;
    }

    size_t expanded_length = strlen(expanded);
    free(expanded);
    dlclose(wrapper);

    if (expanded_length != EXPANSION_BUFFER_SIZE - 1) {
        fprintf(
            stderr,
            "Error: expanded value has length %zu; expected %zu.\n",
            expanded_length,
            (size_t)(EXPANSION_BUFFER_SIZE - 1)
        );
        return 1;
    }

    return 0;
}
EOF

  gcc -fsanitize=address -g -O0 \
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -ldl

  echo "=== Run shell variable expansion bounds ASan test ==="
  if ! ASAN_OPTIONS=detect_stack_use_after_return=1:detect_leaks=$detect_leaks \
    "$test_dir/test" "$PWD/src/vdi_wrapper/build/libvdi-asan.so"; then
    echo "Error: shell variable expansion bounds test failed."
    return 1
  fi
}

run_log_path_allocation_test() {
  # This test calls log_call() directly so it checks log-path allocations
  # without invoking the wrapped file operations.
  local test_dir="$TEST_ROOT/log-path-allocation"
  local logs_dir="$test_dir/logs"
  local detect_leaks=1

  if [ "$(uname -m)" = "riscv64" ]; then
    detect_leaks=0
  fi

  mkdir -p "$logs_dir"

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#if defined(__riscv)
extern size_t __sanitizer_get_current_allocated_bytes(void);
#endif


int run_log_call(int (*log_call)(const char *, int, char **)) {
    return log_call("log-path-allocation-test", 0, NULL);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        return 2;
    }

    void *wrapper = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (wrapper == NULL) {
        fprintf(stderr, "Error: dlopen() failed: %s\n", dlerror());
        return 2;
    }

    int (*log_call)(const char *, int, char **) = dlsym(wrapper, "log_call");
    if (log_call == NULL) {
        fprintf(stderr, "Error: log_call() is unavailable: %s\n", dlerror());
        dlclose(wrapper);
        return 2;
    }

#if defined(__riscv)
    for (int iteration = 0; iteration < 2; iteration++) {
        if (run_log_call(log_call) != EXIT_SUCCESS) {
            dlclose(wrapper);
            return 1;
        }
    }

    size_t allocated_before = __sanitizer_get_current_allocated_bytes();
    for (int iteration = 0; iteration < 3; iteration++) {
        if (run_log_call(log_call) != EXIT_SUCCESS) {
            dlclose(wrapper);
            return 1;
        }
    }
    size_t allocated_after = __sanitizer_get_current_allocated_bytes();

    if (allocated_after > allocated_before) {
        fprintf(stderr, "Error: log_call leaked %zu byte(s) across 3 calls.\n", allocated_after - allocated_before);
        dlclose(wrapper);
        return 1;
    }
#else
    if (run_log_call(log_call) != EXIT_SUCCESS) {
        dlclose(wrapper);
        return 1;
    }
#endif

    dlclose(wrapper);
    return 0;
}
EOF

  gcc -fsanitize=address -g -O0 \
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -ldl

  echo "=== Run log-path allocation ASan test ==="
  if ! ASAN_OPTIONS=detect_stack_use_after_return=1:detect_leaks=$detect_leaks \
    VDI_LOG_DIR="$logs_dir" \
    VDI_LOG_FILE_PREFIX="allocation-test." \
    "$test_dir/test" "$PWD/src/vdi_wrapper/build/libvdi-asan.so"; then
    echo "Error: log-path allocation test failed."
    return 1
  fi

  if [ "$(find "$logs_dir" -type f -name '*.log' | wc -l)" -eq 0 ]; then
    echo "Error: no log-path allocation test log file was created."
    return 1
  fi

  unset VDI_LOG_DIR
  unset VDI_LOG_FILE_PREFIX
}

run_download_allocation_ownership_test() {
  # This test calls download() directly so it checks the ownership of
  # download_base and local_filename without unrelated logging allocations.
  local test_dir="$TEST_ROOT/download-allocation-ownership"
  local downloads_dir="$test_dir/downloads"
  local port=8001
  local detect_leaks=1

  if [ "$(uname -m)" = "riscv64" ]; then
    detect_leaks=0
  fi

  mkdir -p "$test_dir"
  start_http_server "$test_dir/http" "$port"
  wait_for_http_server "$port" "$test_dir/http"

  cat >"$test_dir/openssl.supp" <<'EOF'
leak:CRYPTO_malloc
leak:CRYPTO_zalloc
EOF

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#if defined(__riscv)
extern size_t __sanitizer_get_current_allocated_bytes(void);
#endif


int run_download(int (*download)(const char *, char **), const char *url) {
    char *local_path = NULL;
    if (download(url, &local_path) != 0) {
        return 1;
    }
    if (local_path == NULL || access(local_path, R_OK) != 0) {
        free(local_path);
        return 1;
    }

    free(local_path);
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 3) {
        return 2;
    }

    void *wrapper = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (wrapper == NULL) {
        fprintf(stderr, "Error: dlopen() failed: %s\n", dlerror());
        return 2;
    }

    int (*download)(const char *, char **) = dlsym(wrapper, "download");
    if (download == NULL) {
        fprintf(stderr, "Error: download() is unavailable: %s\n", dlerror());
        dlclose(wrapper);
        return 2;
    }

#if defined(__riscv)
    for (int iteration = 0; iteration < 2; iteration++) {
        if (run_download(download, argv[2]) != 0) {
            dlclose(wrapper);
            return 1;
        }
    }

    size_t allocated_before = __sanitizer_get_current_allocated_bytes();
    for (int iteration = 0; iteration < 3; iteration++) {
        if (run_download(download, argv[2]) != 0) {
            dlclose(wrapper);
            return 1;
        }
    }
    size_t allocated_after = __sanitizer_get_current_allocated_bytes();

    if (allocated_after > allocated_before) {
        fprintf(stderr, "Error: download leaked %zu byte(s) across 3 calls.\n", allocated_after - allocated_before);
        dlclose(wrapper);
        return 1;
    }
#else
    if (run_download(download, argv[2]) != 0) {
        dlclose(wrapper);
        return 1;
    }
#endif

    dlclose(wrapper);
    return 0;
}
EOF

  gcc -fsanitize=address -g -O0 \
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -ldl

  run_download_allocation_ownership_case() {
    local label=$1
    local download_base=$2
    local url=$3

    echo "=== Run download allocation ownership test: $label ==="
    if [ -n "$download_base" ]; then
      export VDI_DOWNLOAD_BASE="$download_base"
    else
      unset VDI_DOWNLOAD_BASE
    fi

    if ! ASAN_OPTIONS=detect_stack_use_after_return=1:detect_leaks=$detect_leaks \
      LSAN_OPTIONS=suppressions="$test_dir/openssl.supp" \
      "$test_dir/test" "$PWD/src/vdi_wrapper/build/libvdi-asan.so" "$url"; then
      echo "Error: download allocation ownership test failed: $label."
      return 1
    fi
  }

  run_download_allocation_ownership_case \
    "environment download base and URL filename" \
    "$downloads_dir" \
    "http://127.0.0.1:$port/from-url.txt"

  run_download_allocation_ownership_case \
    "environment download base and generated filename" \
    "$downloads_dir" \
    "http://127.0.0.1:$port/"

  run_download_allocation_ownership_case \
    "default download base and URL filename" \
    "" \
    "http://127.0.0.1:$port/from-url.txt"

  run_download_allocation_ownership_case \
    "default download base and generated filename" \
    "" \
    "http://127.0.0.1:$port/"

  unset VDI_DOWNLOAD_BASE
  stop_http_server
}

run_download_return_path_test() {
  # This test focuses on the returned download path by:
  # - VDI_DOWNLOAD_BASE is unset, so download_base is heap-allocated.
  # - The URL has no filename, so local_filename is heap-allocated.
  # - LeakSanitizer is disabled, while ASan memory-error checks remain enabled.
  local test_dir="$TEST_ROOT/download-return-path"
  local port=8000

  mkdir -p "$test_dir/logs"
  start_http_server "$test_dir/http" "$port"
  wait_for_http_server "$port" "$test_dir/http"

  cat >"$test_dir/test.c" <<'EOF'
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
    -o "$test_dir/test" \
    "$test_dir/test.c"

  ASAN_RUNTIME=$(gcc -print-file-name=libasan.so)
  if [ ! -f "$ASAN_RUNTIME" ]; then
    ASAN_RUNTIME=$(ldconfig -p | awk '/libasan\.so/ {print $NF; exit}')
  fi

  echo "=== Run download return-path ASan test ==="
  unset VDI_DOWNLOAD_BASE

  LD_PRELOAD="$ASAN_RUNTIME:$PWD/src/vdi_wrapper/build/libvdi-asan.so" \
  ASAN_OPTIONS=detect_stack_use_after_return=1:detect_leaks=0 \
  VDI_LOG_DIR="$TEST_ROOT/download-return-path/logs" \
  "$test_dir/test" >"$test_dir/test-output.txt"

  cat "$test_dir/test-output.txt"

  if [ "$(cat "$test_dir/test-output.txt")" != "hello from vdi" ]; then
    echo "Error: unexpected download return-path test output."
    return 1
  fi

  if [ "$(find "$test_dir/logs" -type f -name '*.log' | wc -l)" -eq 0 ]; then
    echo "Error: no download return-path log file was created."
    return 1
  fi

  stop_http_server
}

run_open_access_flags_mapping_test
run_shell_variable_expansion_bounds_test
run_log_path_allocation_test
run_download_allocation_ownership_test
run_download_return_path_test

echo "libvdi wrapper ASan tests passed."
