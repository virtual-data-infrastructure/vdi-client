# Changelog

## [0.2.0] - 2026-10-11

This release adds `riscv64` architecture support and improves the release
pipeline. Wheels are now published to PyPI for x86_64, aarch64, and riscv64,
bundling support for EESSI 2023.06, 2025.06, and 2026.06 (riscv64 only
supports EESSI 2026.06).
Available on [PyPI](https://pypi.org/project/vdi-client/).

### Added

- `riscv64` architecture support: build and test `manylinux2014_riscv64`
  fat wheels via QEMU emulation using the EESSI `debian13-riscv64`
  build-node container with CernVM-FS (#56, #57)
- Shared wheel test script (`.github/scripts/test-wheel.sh`) reused by
  both regular and riscv64 test jobs (#57)
- Logo on PyPI project page (#54)

### Changed

- Simplify pipeline dependencies: `publish` depends only on test jobs,
  `release` depends only on `publish` (#57)
- Add `actions/checkout` to test jobs that were missing it (#57)
- Rework PyPI project page description (#54)


## [0.1.1] - 2026-10-10

This is minor bug fix release of the vdi-client.

Available on [PyPI](https://pypi.org/project/vdi-client/).

### Changed

- include CPU architecture family in name of wheels (#47)
- fix argument to build platform-specific wheels (#49)


## [0.1.0] - 2026-10-10

This is the first release of the vdi-client, providing client tools for the
virtual data infrastructure: a C wrapper library (`libvdi.so`) that intercepts
file-system calls via `LD_PRELOAD`, and a Python CLI (`vdi`) with `run`,
`view`, and `log` subcommands. Wheels are published to PyPI for x86_64 and
aarch64, bundling support for EESSI 2023.06, 2025.06, and 2026.06.
Available on [PyPI](https://pypi.org/project/vdi-client/).

### Added

- `libvdi.so` C wrapper library intercepting file-system calls via
  `LD_PRELOAD`, built against the EESSI compatibility layer with embedded
  RUNPATH for dependency resolution (#1)
- Logging of intercepted calls with timestamp (#2), PID/PPID/PGID (#3),
  program name and arguments (#4), working directory (#6), username and
  home (#7), hostname/IP address (#8), start/elapsed time (#9), and debug
  levels with constructor/destructor (#10)
- URL download for `open()` calls when the pathname is `http(s)://` or
  `ftp://` (#17), and `freopen()` interception (#18)
- `vdi` CLI tool with `run` and `view` subcommands (#19), later ported to
  Python (#37), plus `vdi log` to list, show, and clean up log files (#39)
- Makefiles for building, installing, and cleaning the wrapper library and
  CLI tool (#12)
- Python package (`vdi_client`) with type annotations, docstrings, SPDX
  license headers, and tooling: ruff, mypy, pyright, pytest with coverage,
  codespell, pymarkdownlnt (#36)
- Fat wheel packaging: one wheel per architecture (x86_64, aarch64)
  bundling `libvdi_eessi*.so` for EESSI 2023.06, 2025.06, and 2026.06;
  runtime selects the matching library from `EESSI_EPREFIX` (#38, #42)
- GitHub Actions release workflow: builds, tests, and publishes wheels to
  PyPI via OIDC trusted publishing, with CI verification against each EESSI
  version for both architectures (#40, #42)
- README with setup, usage, example, and releasing documentation
  (#1, #12, #36, #40)
- Thread-safe logging via mutex with persistent log file descriptor;
  robust memory management across `log_call()`, `download()`, and
  `get_directory()`; correct `O_ACCMODE` flag masking; bounds-checked
  environment variable expansion; variadic `open64()` wrapper matching
  `open`/`openat` (#43)
- Automated GitHub Release creation with changelog-derived release notes
  and wheel assets (#43)
