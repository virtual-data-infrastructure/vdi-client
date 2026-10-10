# VDI client

Client tools for the [virtual data infrastructure](https://github.com/virtual-data-infrastructure).

The `vdi` command-line tool intercepts file-system calls made by a program,
logs them, and transparently downloads files from a VDI server via URL when
needed. This lets you run scientific workloads against remote data without
manually staging files. Accesses are tracked and served on demand.

## Installation

```bash
pip install vdi-client
```

## Usage

The `vdi` CLI provides three subcommands:

- **`vdi run`**: run a program with VDI extensions (file-system interception,
  logging, transparent URL download).
- **`vdi view`**: create, list, delete, upload to, and download from views on
  a VDI server.
- **`vdi log`**: list, show, and clean up VDI log files.

### Examples

Run a program with VDI extensions:

```bash
vdi run python my_script.py
```

List views on a VDI server:

```bash
vdi view --base-url https://vdi.example.org list
```

Show the contents of a log file:

```bash
vdi log show --pid 12345
```

Run `vdi -h` for the full usage overview.

## Supported platforms

- Linux `x86_64` and `aarch64`
- EESSI stack versions 2023.06, 2025.06, and 2026.06

## License

GPL-2.0-only
