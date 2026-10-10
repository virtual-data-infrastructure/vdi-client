# Changelog

## [0.1.0] - 2026-10-10

This is the first release of the vdi-client, providing client tools for the
virtual data infrastructure: a C wrapper library (`libvdi.so`) that intercepts
file-system calls via `LD_PRELOAD`, and a Python CLI (`vdi`) with `run`,
`view`, and `log` subcommands. Wheels are published to PyPI for x86_64 and
aarch64, bundling support for EESSI 2023.06, 2025.06, and 2026.06.
Available on [PyPI](https://pypi.org/project/vdi-client/).

### Added

- `libvdi.so` C wrapper library that intercepts file-system calls via
  `LD_PRELOAD` and logs them, built against the EESSI compatibility layer
  with RUNPATH embedded for EESSI dependency resolution (#1)
- Logging of intercepted calls including timestamp (#2), PID, PPID, PGID
  (#3), program name and arguments (#4), current working directory (#6),
  username and user home (#7), hostname/IP address (#8), and program
  start/elapsed time (#9)
- Debug levels with constructor and destructor for the wrapper library
  (#10)
- Download feature for `open()` calls when the pathname is a URL (#17)
- Interception of `freopen()` in addition to `open()` (#18)
- `vdi` CLI tool with `run` and `view` subcommands (#19)
- Makefiles for building, installing, and cleaning the wrapper library
  and CLI tool (#12)
- Python package (`vdi_client`) with type annotations, docstrings, SPDX
  license headers, and project tooling: ruff, mypy, pyright, pytest with
  coverage, codespell, pymarkdownlnt (#36)
- Python CLI port of the bash `vdi` script (#37)
- `vdi log` subcommand to list, show, and clean up VDI log files (#39)
- Build integration for platform wheels with EESSI RUNPATH (#38)
- Fat wheel packaging: one wheel per architecture (x86_64, aarch64)
  bundling `libvdi_eessi*.so` for all supported EESSI versions (2023.06,
  2025.06, 2026.06); runtime selects the matching library from
  `EESSI_EPREFIX` (#42)
- GitHub Actions release workflow: builds, tests, and publishes wheels
  to PyPI via OIDC trusted publishing; creates GitHub Releases with
  changelog-derived release notes (#40, #42)
- CI test job verifying built wheels against each EESSI version for both
  architectures (#42)
- README with setup, usage, example, and releasing documentation
  (#1, #12, #36, #40)
