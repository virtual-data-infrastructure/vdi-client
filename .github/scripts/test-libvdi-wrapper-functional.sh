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
source "$REPO_ROOT/.github/scripts/lib/http-server.sh"

echo "=== Build wrapper ==="
make clean
make -C src/vdi_wrapper compile

TEST_ROOT=$(mktemp -d)

cleanup() {
  stop_http_server
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
    '$13 == "open64" && $14 == pathname { print NF; found = 1; exit }
     END { if (!found) print 0 }' \
    "$log_file")
  if [ "$two_argument_field_count" -ne 15 ]; then
    echo "Error: two-argument open64() logged $two_argument_field_count fields; expected 15."
    return 1
  fi

  local three_argument_field_count
  three_argument_field_count=$(awk \
    -v pathname="$created_file" \
    '$13 == "open64" && $14 == pathname { print NF; found = 1; exit }
     END { if (!found) print 0 }' \
    "$log_file")
  if [ "$three_argument_field_count" -ne 16 ]; then
    echo "Error: three-argument open64() logged $three_argument_field_count fields; expected 16."
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

run_download_reentrancy_test() {
  local test_dir="$TEST_ROOT/download-reentrancy"
  local server_dir="$test_dir/http"
  local port_file="$server_dir/port"
  local reference_logs_dir="$test_dir/reference-logs"
  local direct_logs_dir="$test_dir/direct-logs"
  local open_logs_dir="$test_dir/open-logs"
  local downloads_dir="$test_dir/downloads"
  local openssl_config="$test_dir/openssl.cnf"

  mkdir -p "$reference_logs_dir" "$direct_logs_dir" "$open_logs_dir" "$downloads_dir"
  touch "$openssl_config"
  start_http_server "$server_dir" "$port_file"
  wait_for_http_server "$server_dir" "$port_file"

  local port
  port=$(cat "$port_file")
  local url="http://127.0.0.1:$port/"

  cat >"$test_dir/test.c" <<'EOF'
#include <curl/curl.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 3) {
        return 2;
    }

    if (strcmp(argv[1], "reference") == 0) {
        CURLcode result = curl_global_init(CURL_GLOBAL_DEFAULT);
        if (result != CURLE_OK) {
            return 1;
        }

        CURL *curl = curl_easy_init();
        if (curl == NULL) {
            curl_global_cleanup();
            return 1;
        }

        curl_easy_cleanup(curl);
        curl_global_cleanup();
        return 0;
    }

    if (strcmp(argv[1], "direct") == 0) {
        int (*download)(const char *, char **) = dlsym(RTLD_DEFAULT, "download");
        if (download == NULL) {
            fprintf(stderr, "Error: download() is unavailable.\n");
            return 2;
        }

        char *local_path = NULL;
        if (download(argv[2], &local_path) != 0) {
            fprintf(stderr, "Error: download() failed.\n");
            return 1;
        }

        if (local_path == NULL || access(local_path, R_OK) != 0) {
            fprintf(stderr, "Error: download() returned an unusable path.\n");
            free(local_path);
            return 1;
        }
        free(local_path);

        if (fwrite("x", 1, 1, stderr) != 1) {
            fprintf(stderr, "Error: application fwrite() failed.\n");
            return 1;
        }
        return 0;
    } else {
        FILE *file = fopen(argv[2], "r");
        if (file == NULL) {
            fprintf(stderr, "Error: fopen() failed.\n");
            return 1;
        }

        char body[16] = {0};
        if (fread(body, 1, sizeof(body) - 1, file) != 15 ||
            strcmp(body, "hello from vdi\n") != 0) {
            fprintf(stderr, "Error: downloaded content mismatch.\n");
            fclose(file);
            return 1;
        }

        if (fclose(file) != 0) {
            fprintf(stderr, "Error: fclose() failed.\n");
            return 1;
        }
        return 0;
    }
}
EOF

  gcc -Wall -Wextra -Werror -g -O0 \
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -lcurl \
    -ldl

  echo "=== Run curl/OpenSSL nested-call reference test ==="
  if ! LD_PRELOAD="$PWD/src/vdi_wrapper/build/libvdi.so" \
    VDI_LOG_DIR="$reference_logs_dir" \
    VDI_LOG_FILE_PREFIX="download-reference." \
    OPENSSL_CONF="$openssl_config" \
    "$test_dir/test" reference "$url"; then
    echo "Error: curl/OpenSSL nested-call reference test failed."
    return 1
  fi

  local reference_log_file
  reference_log_file=$(find "$reference_logs_dir" -type f -name '*.log' -print -quit)
  if [ -z "$reference_log_file" ]; then
    echo "Error: curl/OpenSSL nested-call reference test log file was not created."
    return 1
  fi

  local reference_open_count
  reference_open_count=$(awk -v config="$openssl_config" '
    ($13 == "fopen" || $13 == "fopen64" || $13 == "freopen" ||
     $13 == "open" || $13 == "open64") && $14 == config { count++ }
    $13 == "fopenat" && $15 == config { count++ }
    END { print count + 0 }
  ' "$reference_log_file")
  if [ "$reference_open_count" -lt 1 ]; then
    echo "Error: curl/OpenSSL reference test did not produce a nested open-family log entry."
    return 1
  fi

  echo "=== Run direct download reentrancy test ==="
  local direct_stderr_file="$test_dir/direct-stderr.txt"
  if ! LD_PRELOAD="$PWD/src/vdi_wrapper/build/libvdi.so" \
    VDI_DOWNLOAD_BASE="$downloads_dir" \
    VDI_LOG_DIR="$direct_logs_dir" \
    VDI_LOG_FILE_PREFIX="download-direct." \
    OPENSSL_CONF="$openssl_config" \
    "$test_dir/test" direct "$url" 2>"$direct_stderr_file"; then
    echo "Error: direct download reentrancy test failed."
    cat "$direct_stderr_file"
    return 1
  fi

  local direct_log_file
  direct_log_file=$(find "$direct_logs_dir" -type f -name '*.log' -print -quit)
  if [ -z "$direct_log_file" ]; then
    echo "Error: direct download guard-restoration test log file was not created."
    return 1
  fi

  local direct_log_line_count
  direct_log_line_count=$(wc -l <"$direct_log_file" | tr -d ' ')
  if [ "$direct_log_line_count" -ne 1 ]; then
    echo "Error: direct download created $direct_log_line_count log entries; expected 1."
    echo "=== Unexpected direct download log ==="
    cat "$direct_log_file"
    return 1
  fi

  local direct_fwrite_count
  direct_fwrite_count=$(awk '$13 == "fwrite" && $14 == 1 && $15 == 1 { count++ } END { print count + 0 }' "$direct_log_file")
  if [ "$direct_fwrite_count" -ne 1 ]; then
    echo "Error: found $direct_fwrite_count application fwrite log entries; expected 1."
    return 1
  fi

  local direct_internal_open_count
  direct_internal_open_count=$(awk -v config="$openssl_config" '
    ($13 == "fopen" || $13 == "fopen64" || $13 == "freopen" ||
     $13 == "open" || $13 == "open64") && $14 == config { count++ }
    $13 == "fopenat" && $15 == config { count++ }
    END { print count + 0 }
  ' "$direct_log_file")
  if [ "$direct_internal_open_count" -ne 0 ]; then
    echo "Error: found $direct_internal_open_count internal open-family log entries; expected 0."
    return 1
  fi

  echo "=== Run open-family download reentrancy test ==="
  if ! LD_PRELOAD="$PWD/src/vdi_wrapper/build/libvdi.so" \
    VDI_DOWNLOAD_BASE="$downloads_dir" \
    VDI_LOG_DIR="$open_logs_dir" \
    VDI_LOG_FILE_PREFIX="download-open." \
    OPENSSL_CONF="$openssl_config" \
    "$test_dir/test" open "$url"; then
    echo "Error: open-family download reentrancy test failed."
    return 1
  fi

  local open_log_file
  open_log_file=$(find "$open_logs_dir" -type f -name '*.log' -print -quit)
  if [ -z "$open_log_file" ]; then
    echo "Error: open-family download reentrancy test log file was not created."
    return 1
  fi

  local open_log_line_count
  open_log_line_count=$(wc -l <"$open_log_file" | tr -d ' ')
  if [ "$open_log_line_count" -ne 2 ]; then
    echo "Error: open-family download created $open_log_line_count log entries; expected 2."
    echo "=== Unexpected open-family download log ==="
    cat "$open_log_file"
    return 1
  fi

  local fopen_count
  fopen_count=$(awk -v url="$url" '$13 == "fopen" && $14 == url { count++ } END { print count + 0 }' "$open_log_file")
  if [ "$fopen_count" -ne 1 ]; then
    echo "Error: found $fopen_count fopen log entries; expected 1."
    return 1
  fi

  local application_fclose_count
  application_fclose_count=$(awk '$13 == "fclose" { count++ } END { print count + 0 }' "$open_log_file")
  if [ "$application_fclose_count" -ne 1 ]; then
    echo "Error: found $application_fclose_count application fclose log entries; expected 1."
    return 1
  fi

  local internal_io_count
  internal_io_count=$(awk '
    $13 == "fwrite" || $13 == "write" { count++ }
    END { print count + 0 }
  ' "$open_log_file")
  if [ "$internal_io_count" -ne 0 ]; then
    echo "Error: found $internal_io_count internal I/O log entries; expected 0."
    return 1
  fi

  stop_http_server
}

run_write_close_interception_test() {
  local test_dir="$TEST_ROOT/write-close-interception"
  local default_logs_dir="$test_dir/default-logs"
  local threshold_logs_dir="$test_dir/threshold-logs"
  local output_file="$test_dir/output.txt"

  mkdir -p "$default_logs_dir" "$threshold_logs_dir"

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 4) {
        return 2;
    }

    if (strcmp(argv[2], "default") != 0 && strcmp(argv[2], "threshold") != 0) {
        return 2;
    }

    void *wrapper = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (wrapper == NULL) {
        fprintf(stderr, "Error: dlopen() failed: %s\n", dlerror());
        return 2;
    }

    int (*fclose_wrapper)(FILE *) = dlsym(wrapper, "fclose");
    size_t (*fwrite_wrapper)(const void *, size_t, size_t, FILE *) = dlsym(wrapper, "fwrite");
    ssize_t (*write_wrapper)(int, const void *, size_t) = dlsym(wrapper, "write");

    if (fclose_wrapper == NULL || fwrite_wrapper == NULL || write_wrapper == NULL) {
        fprintf(stderr, "Error: fclose, fwrite, or write is unavailable: %s\n", dlerror());
        dlclose(wrapper);
        return 2;
    }

    if (strcmp(argv[2], "default") == 0) {
        FILE *stream = fopen(argv[3], "w");
        if (stream == NULL) {
            fprintf(stderr, "Error: fopen() failed: %s\n", strerror(errno));
            dlclose(wrapper);
            return 1;
        }

        if (fwrite_wrapper("x", 1, 1, stream) != 1) {
            fprintf(stderr, "Error: fwrite() did not write the expected item count.\n");
            dlclose(wrapper);
            return 1;
        }

        if (fclose_wrapper(stream) != 0) {
            fprintf(stderr, "Error: fclose() failed: %s\n", strerror(errno));
            dlclose(wrapper);
            return 1;
        }

        int fd = open(argv[3], O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (fd < 0) {
            fprintf(stderr, "Error: open() failed: %s\n", strerror(errno));
            dlclose(wrapper);
            return 1;
        }

        if (write_wrapper(fd, "y", 1) != 1) {
            fprintf(stderr, "Error: write() did not write the expected byte count.\n");
            close(fd);
            dlclose(wrapper);
            return 1;
        }

        if (close(fd) != 0) {
            fprintf(stderr, "Error: close() failed: %s\n", strerror(errno));
            dlclose(wrapper);
            return 1;
        }
    } else {
        int fd = open(argv[3], O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (fd < 0) {
            fprintf(stderr, "Error: open() failed: %s\n", strerror(errno));
            dlclose(wrapper);
            return 1;
        }

        if (write_wrapper(fd, "x", 1) != 1) {
            fprintf(stderr, "Error: one-byte write() did not write the expected byte count.\n");
            close(fd);
            dlclose(wrapper);
            return 1;
        }

        if (write_wrapper(fd, "yy", 2) != 2) {
            fprintf(stderr, "Error: two-byte write() did not write the expected byte count.\n");
            close(fd);
            dlclose(wrapper);
            return 1;
        }

        if (close(fd) != 0) {
            fprintf(stderr, "Error: close() failed: %s\n", strerror(errno));
            dlclose(wrapper);
            return 1;
        }
    }

    dlclose(wrapper);
    return 0;
}
EOF

  gcc -Wall -Wextra -Werror -g -O0 \
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -ldl

  echo "=== Run write and close interception test ==="
  if ! VDI_LOG_DIR="$default_logs_dir" \
    VDI_LOG_FILE_PREFIX="write-close-default." \
    "$test_dir/test" \
    "$PWD/src/vdi_wrapper/build/libvdi.so" \
    default \
    "$output_file"; then
    echo "Error: write and close interception test failed."
    return 1
  fi

  if ! VDI_LOG_DIR="$threshold_logs_dir" \
    VDI_LOG_FILE_PREFIX="write-close-threshold." \
    VDI_LOG_MIN_WRITE_BYTES=2 \
    "$test_dir/test" \
    "$PWD/src/vdi_wrapper/build/libvdi.so" \
    threshold \
    "$output_file"; then
    echo "Error: write threshold test failed."
    return 1
  fi

  local default_log_file
  default_log_file=$(find "$default_logs_dir" -type f -name '*.log' -print -quit)
  if [ -z "$default_log_file" ]; then
    echo "Error: no write and close interception test log file was created."
    return 1
  fi

  local fwrite_count
  fwrite_count=$(awk '$13 == "fwrite" && $14 == 1 && $15 == 1 && NF == 16 { count++ } END { print count + 0 }' "$default_log_file")
  if [ "$fwrite_count" -ne 1 ]; then
    echo "Error: found $fwrite_count matching fwrite log entries; expected 1."
    return 1
  fi

  local fclose_count
  fclose_count=$(awk '$13 == "fclose" && NF == 14 { count++ } END { print count + 0 }' "$default_log_file")
  if [ "$fclose_count" -ne 1 ]; then
    echo "Error: found $fclose_count matching fclose log entries; expected 1."
    return 1
  fi

  local write_count
  write_count=$(awk '$13 == "write" && $15 == 1 && NF == 15 { count++ } END { print count + 0 }' "$default_log_file")
  if [ "$write_count" -ne 1 ]; then
    echo "Error: found $write_count matching one-byte write log entries; expected 1."
    return 1
  fi

  local threshold_log_file
  threshold_log_file=$(find "$threshold_logs_dir" -type f -name '*.log' -print -quit)
  if [ -z "$threshold_log_file" ]; then
    echo "Error: no write threshold test log file was created."
    return 1
  fi

  local suppressed_write_count
  suppressed_write_count=$(awk '$13 == "write" && $15 == 1 { count++ } END { print count + 0 }' "$threshold_log_file")
  if [ "$suppressed_write_count" -ne 0 ]; then
    echo "Error: found $suppressed_write_count one-byte write log entries; expected 0."
    return 1
  fi

  local logged_write_count
  logged_write_count=$(awk '$13 == "write" && $15 == 2 && NF == 15 { count++ } END { print count + 0 }' "$threshold_log_file")
  if [ "$logged_write_count" -ne 1 ]; then
    echo "Error: found $logged_write_count two-byte write log entries; expected 1."
    return 1
  fi
}

run_process_start_time_parsing_test
run_open64_variadic_signature_test
run_download_error_reporting_test
run_download_reentrancy_test
run_write_close_interception_test

echo "libvdi wrapper functional tests passed."
