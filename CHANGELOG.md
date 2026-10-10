# Changelog

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
