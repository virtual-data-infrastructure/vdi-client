# Command-line usage

Run `vdi` or `vdi --help` for an overview. Every subcommand also accepts `-h`
for its own help.

## Common options

These options are accepted by `run`, `view`, and `log`:

| Option | Description |
|--------|-------------|
| `--base-url URL` | VDI server base URL |
| `--config PATH` | Alternative configuration file |
| `--dry-run` | Print what would happen without performing it |
| `-v`, `--verbose` | Print additional diagnostic information |
| `-h`, `--help` | Show command help |

## `vdi run`

Run a program with the VDI wrapper library loaded:

```bash
vdi run PROGRAM [PROGRAM_ARGS]
```

Additional options:

| Option | Description |
|--------|-------------|
| `--lib PATH` | Use a specific `libvdi.so` instead of the automatic choice |

Examples:

```bash
vdi run --dry-run ls -la
vdi run python examples/map_plot.py data/no.json --out outputs
vdi run --lib ./lib64/libvdi.so python my_script.py
```

If no active EESSI version can be detected, or the selected library was built
for a different EESSI version, `vdi run` reports an error instead of starting
the program.

## `vdi view`

Manage views on a VDI server:

```bash
vdi view SUBCOMMAND [ARGUMENTS]
```

| Subcommand | Arguments | Description |
|------------|-----------|-------------|
| `create` | `VIEW_NAME` | Create a view |
| `delete` | `VIEW_NAME` | Delete a view |
| `files` | `VIEW_NAME` | List files in a view |
| `geturl` | `VIEW_NAME FILE_NAME` | Print a file download URL |
| `list` | none | List all views |
| `remove` | `VIEW_NAME FILE_NAME` | Remove a file from a view |
| `upload` | `VIEW_NAME FILE_PATH` | Upload a local file to a view |

Examples:

```bash
vdi view list
vdi view create experiment-results
vdi view upload experiment-results outputs/no.json_map.png
vdi view files experiment-results
vdi view geturl experiment-results no.json_map.png
```

Most view operations print a human-readable summary. Use `--dry-run` to see the
HTTP request that would be made.

The current view commands do not cache responses locally or work offline.

## `vdi log`

Inspect and clean up logs created by `vdi run`:

```bash
vdi log list
vdi log show PID
vdi log clean [--pid PID]
```

All log subcommands accept `--log-dir` and `--log-prefix`. See
[managing VDI logs](logging.md) for sorting, filtering, and cleanup examples.
