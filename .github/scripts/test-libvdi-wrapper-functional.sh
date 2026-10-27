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

run_open64_variadic_signature_test() {
  local test_dir="$TEST_ROOT/open64-variadic-signature"
  local logs_dir="$test_dir/logs"
  local existing_file="$test_dir/existing.txt"
  local created_file="$test_dir/created.txt"

  mkdir -p "$logs_dir"
  printf 'hello from vdi\n' >"$existing_file"

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 4) {
        return 2;
    }

    void *wrapper = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (wrapper == NULL) {
        fprintf(stderr, "Error: dlopen() failed: %s\n", dlerror());
        return 2;
    }

    int (*open64_wrapper)(const char *, int, ...) = dlsym(wrapper, "open64");
    if (open64_wrapper == NULL) {
        fprintf(stderr, "Error: open64() is unavailable: %s\n", dlerror());
        dlclose(wrapper);
        return 2;
    }

    int existing_fd = open64_wrapper(argv[2], O_RDONLY);
    if (existing_fd < 0) {
        fprintf(stderr, "Error: two-argument open64() failed: %s\n", strerror(errno));
        dlclose(wrapper);
        return 1;
    }
    close(existing_fd);

    umask(0);
    int created_fd = open64_wrapper(argv[3], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (created_fd < 0) {
        fprintf(stderr, "Error: three-argument open64() failed: %s\n", strerror(errno));
        dlclose(wrapper);
        return 1;
    }
    close(created_fd);

    struct stat file_status;
    if (stat(argv[3], &file_status) != 0) {
        fprintf(stderr, "Error: created file is unavailable: %s\n", strerror(errno));
        dlclose(wrapper);
        return 1;
    }
    if ((file_status.st_mode & 0777) != 0600) {
        fprintf(
            stderr,
            "Error: created file mode is %04o; expected 0600.\n",
            file_status.st_mode & 0777
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

  echo "=== Run open64 variadic signature test ==="
  if ! VDI_LOG_DIR="$logs_dir" \
    VDI_LOG_FILE_PREFIX="open64-variadic-test." \
    "$test_dir/test" \
    "$PWD/src/vdi_wrapper/build/libvdi.so" \
    "$existing_file" \
    "$created_file"; then
    echo "Error: open64 variadic signature test failed."
    return 1
  fi

  if [ "$(find "$logs_dir" -type f -name '*.log' | wc -l)" -eq 0 ]; then
    echo "Error: no open64 variadic signature test log file was created."
    return 1
  fi

  local log_file
  log_file=$(find "$logs_dir" -type f -name '*.log' -print -quit)

  local two_argument_field_count
  two_argument_field_count=$(awk \
    -v pathname="$existing_file" \
    '$11 == "open64" && $12 == pathname { print NF; exit }' \
    "$log_file")
  if [ "$two_argument_field_count" -ne 13 ]; then
    echo "Error: two-argument open64() logged $two_argument_field_count fields; expected 13."
    return 1
  fi

  local three_argument_field_count
  three_argument_field_count=$(awk \
    -v pathname="$created_file" \
    '$11 == "open64" && $12 == pathname { print NF; exit }' \
    "$log_file")
  if [ "$three_argument_field_count" -ne 14 ]; then
    echo "Error: three-argument open64() logged $three_argument_field_count fields; expected 14."
    return 1
  fi
}

run_download_error_reporting_test() {
  local test_dir="$TEST_ROOT/download-error-reporting"
  local downloads_dir="$test_dir/downloads"

  mkdir -p "$downloads_dir"

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc != 2) {
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

    char *local_path = NULL;
    errno = 0;
    int result = download("http://127.0.0.1:1/", &local_path);

    printf("download() returned %d; errno is %d.\n", result, errno);

    if (result != EXIT_FAILURE) {
        fprintf(stderr, "Error: download() returned %d; expected EXIT_FAILURE.\n", result);
        dlclose(wrapper);
        return 1;
    }

    if (errno != EIO) {
        fprintf(stderr, "Error: download() set errno to %d; expected EIO (%d).\n", errno, EIO);
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

  echo "=== Run download error reporting test ==="
  if ! VDI_DOWNLOAD_BASE="$downloads_dir" \
    "$test_dir/test" "$PWD/src/vdi_wrapper/build/libvdi.so"; then
    echo "Error: download error reporting test failed."
    return 1
  fi
}

run_process_start_time_parsing_test
run_open64_variadic_signature_test
run_download_error_reporting_test

echo "libvdi wrapper functional tests passed."
