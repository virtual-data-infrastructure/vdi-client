#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
#
# Functional tests for the libvdi.so wrapper.
#
set -euo pipefail

if [ -z "${EESSI_EPREFIX:-}" ]; then
  echo "Error: EESSI_EPREFIX is not set; initialize EESSI before running this test."
  exit 1
fi

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

echo "=== Build wrapper ==="
make clean
make -C src/vdi_wrapper compile

TEST_ROOT=$(mktemp -d)

cleanup() {
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

run_process_start_time_parsing_test() {
  local test_dir="$TEST_ROOT/process-start-time-parsing"

  mkdir -p "$test_dir"

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

long long get_expected_start_time(const char *stat_line) {
    char *closing_parenthesis = strrchr(stat_line, ')');
    if (closing_parenthesis == NULL) {
        return -1;
    }

    char *save_pointer = NULL;
    char *field = strtok_r(closing_parenthesis + 1, " ", &save_pointer);
    for (int field_number = 3; field_number <= 22; field_number++) {
        if (field == NULL) {
            return -1;
        }
        if (field_number == 22) {
            return atoll(field);
        }
        field = strtok_r(NULL, " ", &save_pointer);
    }

    return -1;
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

    long long (*get_process_start_time)(pid_t) = dlsym(wrapper, "get_process_start_time");
    if (get_process_start_time == NULL) {
        fprintf(stderr, "Error: get_process_start_time() is unavailable: %s\n", dlerror());
        dlclose(wrapper);
        return 2;
    }

    char stat_line[4096];
    FILE *stat_file = fopen("/proc/self/stat", "r");
    if (stat_file == NULL || fgets(stat_line, sizeof(stat_line), stat_file) == NULL) {
        if (stat_file != NULL) {
            fclose(stat_file);
        }
        fprintf(stderr, "Error: failed to read /proc/self/stat.\n");
        dlclose(wrapper);
        return 1;
    }
    fclose(stat_file);

    printf("/proc/self/stat: %s\n", stat_line);

    if (strstr(stat_line, "(vdi)test)") == NULL) {
        fprintf(
            stderr,
            "Error: /proc/self/stat does not contain the expected process name.\n"
        );
        dlclose(wrapper);
        return 1;
    }

    long long expected = get_expected_start_time(stat_line);
    long long actual = get_process_start_time(getpid());

    printf("Expected process start time: %lld\n", expected);
    printf("Received process start time: %lld\n", actual);

    if (expected < 0) {
        fprintf(
            stderr,
            "Error: failed to determine expected process start time.\n"
            "The complete diagnostics were printed above.\n"
        );
        dlclose(wrapper);
        return 1;
    }

    if (actual != expected) {
        fprintf(
            stderr,
            "Error: process start time is %lld; expected %lld.\n"
            "The complete diagnostics were printed above.\n",
            actual,
            expected
        );
        dlclose(wrapper);
        return 1;
    }

    dlclose(wrapper);
    return 0;
}
EOF

  gcc -Wall -Wextra -Werror -g -O0 \
    -o "$test_dir/vdi)test" \
    "$test_dir/test.c" \
    -ldl

  echo "=== Run process start-time parsing test ==="
  if ! "$test_dir/vdi)test" "$PWD/src/vdi_wrapper/build/libvdi.so"; then
    echo "Error: process start-time parsing test failed."
    return 1
  fi
}

run_process_start_time_parsing_test

echo "libvdi wrapper functional tests passed."
