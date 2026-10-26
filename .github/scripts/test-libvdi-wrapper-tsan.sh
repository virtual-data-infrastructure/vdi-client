#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
#
# ThreadSanitizer tests for the libvdi.so wrapper.
#
set -euo pipefail

if [ -z "${EESSI_EPREFIX:-}" ]; then
  echo "Error: EESSI_EPREFIX is not set; initialize EESSI before running this test."
  exit 1
fi

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

echo "=== Build TSan-instrumented wrapper ==="
make clean
make tsan

TEST_ROOT=$(mktemp -d)

cleanup() {
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

run_log_call_thread_safety_test() {
  local test_dir="$TEST_ROOT/log-call-thread-safety"
  local logs_dir="$test_dir/logs"
  local expected_lines=80
  local extra_compiler_flags=""

  mkdir -p "$logs_dir"

  if [ "$(uname -m)" = "riscv64" ]; then
    extra_compiler_flags="-no-pie"
  fi

  cat >"$test_dir/test.c" <<'EOF'
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

#define THREAD_COUNT 8
#define CALLS_PER_THREAD 10

struct thread_context {
    int (*log_call)(const char *, int, char **);
    pthread_mutex_t *start_mutex;
    pthread_cond_t *start_condition;
    int *start;
    int failure;
};

void *run_log_calls(void *argument) {
    struct thread_context *context = argument;

    if (pthread_mutex_lock(context->start_mutex) != 0) {
        context->failure = 1;
        return NULL;
    }

    while (*context->start == 0) {
        if (pthread_cond_wait(context->start_condition, context->start_mutex) != 0) {
            context->failure = 1;
            pthread_mutex_unlock(context->start_mutex);
            return NULL;
        }
    }

    if (pthread_mutex_unlock(context->start_mutex) != 0) {
        context->failure = 1;
        return NULL;
    }

    for (int iteration = 0; iteration < CALLS_PER_THREAD; iteration++) {
        if (context->log_call("thread-safety-test", 0, NULL) != EXIT_SUCCESS) {
            context->failure = 1;
            return NULL;
        }
    }

    return NULL;
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

    pthread_mutex_t start_mutex;
    pthread_cond_t start_condition;
    int start = 0;
    if (pthread_mutex_init(&start_mutex, NULL) != 0) {
        dlclose(wrapper);
        return 2;
    }
    if (pthread_cond_init(&start_condition, NULL) != 0) {
        pthread_mutex_destroy(&start_mutex);
        dlclose(wrapper);
        return 2;
    }

    pthread_t threads[THREAD_COUNT];
    struct thread_context contexts[THREAD_COUNT];
    int created_threads = 0;
    int failed = 0;

    for (int index = 0; index < THREAD_COUNT; index++) {
        contexts[index].log_call = log_call;
        contexts[index].start_mutex = &start_mutex;
        contexts[index].start_condition = &start_condition;
        contexts[index].start = &start;
        contexts[index].failure = 0;

        if (pthread_create(&threads[index], NULL, run_log_calls, &contexts[index]) != 0) {
            failed = 1;
            break;
        }
        created_threads++;
    }

    if (pthread_mutex_lock(&start_mutex) != 0) {
        failed = 1;
    } else {
        start = 1;
        if (pthread_cond_broadcast(&start_condition) != 0) {
            failed = 1;
        }
        if (pthread_mutex_unlock(&start_mutex) != 0) {
            failed = 1;
        }
    }

    for (int index = 0; index < created_threads; index++) {
        pthread_join(threads[index], NULL);
    }

    for (int index = 0; index < THREAD_COUNT; index++) {
        failed |= contexts[index].failure;
    }

    pthread_cond_destroy(&start_condition);
    pthread_mutex_destroy(&start_mutex);
    dlclose(wrapper);
    return failed ? 1 : 0;
}
EOF

  gcc -fsanitize=thread -g -O0 \
    $extra_compiler_flags \
    -o "$test_dir/test" \
    "$test_dir/test.c" \
    -pthread \
    -ldl

  echo "=== Run log_call thread-safety TSan test ==="
  if ! TSAN_OPTIONS=halt_on_error=1 \
    VDI_LOG_DIR="$logs_dir" \
    VDI_LOG_FILE_PREFIX="thread-safety-test." \
    "$test_dir/test" "$PWD/src/vdi_wrapper/build/libvdi-tsan.so"; then
    echo "Error: log_call thread-safety test failed."
    return 1
  fi

  local log_file
  log_file=$(find "$logs_dir" -type f -name '*.log' -print -quit)
  if [ -z "$log_file" ]; then
    echo "Error: no log_call thread-safety test log file was created."
    return 1
  fi

  local matching_lines
  matching_lines=$(awk '$NF == "thread-safety-test" { count++ } END { print count + 0 }' "$log_file")
  if [ "$matching_lines" -ne "$expected_lines" ]; then
    echo "Error: expected $expected_lines complete log lines; found $matching_lines."
    return 1
  fi
}

run_log_call_thread_safety_test

echo "libvdi wrapper TSan tests passed."
