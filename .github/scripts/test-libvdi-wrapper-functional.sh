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
#include <sys/prctl.h>
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

int read_process_name(char *process_name, size_t process_name_size) {
    FILE *file = fopen("/proc/self/comm", "r");
    if (file == NULL) {
        return -1;
    }

    if (fgets(process_name, process_name_size, file) == NULL) {
        fclose(file);
        return -1;
    }
    fclose(file);

    process_name[strcspn(process_name, "\n")] = '\0';
    return 0;
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

    if (prctl(PR_SET_NAME, "vdi)test", 0, 0, 0) != 0) {
        fprintf(stderr, "Error: failed to set process name.\n");
        dlclose(wrapper);
        return 2;
    }

    char process_name[64];
    if (read_process_name(process_name, sizeof(process_name)) != 0) {
        fprintf(stderr, "Error: failed to read /proc/self/comm.\n");
        dlclose(wrapper);
        return 1;
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

    printf("Process name: %s\n", process_name);
    printf("/proc/self/stat: %s\n", stat_line);

    long long expected = get_expected_start_time(stat_line);
    long long actual = get_process_start_time(getpid());

    printf("Expected process start time: %lld\n", expected);
    printf("Received process start time: %lld\n", actual);

    if (strcmp(process_name, "vdi)test") != 0) {
        fprintf(
            stderr,
            "Error: process name is '%s'; expected 'vdi)test'.\n",
            process_name
        );
        dlclose(wrapper);
        return 1;
    }

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
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -ldl

  echo "=== Run process start-time parsing test ==="
  if ! "$test_dir/test" "$PWD/src/vdi_wrapper/build/libvdi.so"; then
    echo "Error: process start-time parsing test failed."
    return 1
  fi
}

run_process_start_time_parsing_test

echo "libvdi wrapper functional tests passed."
