# Managing VDI logs

Each `vdi run` execution writes a log under `~/.vdi/logs` by default. Filenames
use the form `vdi_log.PID.log`, where `PID` is the process ID recorded by the
wrapper.

## Location and naming

Log collection is controlled by these environment variables:

```bash
export VDI_LOG_DIR=/tmp/vdi-logs
export VDI_LOG_FILE_PREFIX="vdi_${USER}."
```

The equivalent one-time overrides are `--log-dir` and `--log-prefix`.

## List logs

List logs for the active EESSI version:

```bash
vdi log list
```

Show all EESSI versions:

```bash
vdi log list --all
```

Show size, modification time, program name, and EESSI version:

```bash
vdi log list --long
```

Sort by PID, date, size, or program:

```bash
vdi log list --sort date
vdi log list --sort size --reverse
vdi log list --sort program
```

Select a particular version explicitly:

```bash
vdi log list --eessi-version 2023.06
vdi log list --eessi-version unknown
```

Older logs created before EESSI-version tracking was added are reported as
`unknown`.

## Show a log

Print one log by PID:

```bash
vdi log show 43944
```

The command honors the same EESSI-version filtering as `vdi log list`. Use
`--eessi-version` or `--all` when needed:

```bash
vdi log show --all 43944
```

## Clean up logs

Preview deletion of every collected log:

```bash
vdi log clean --dry-run
```

Delete all logs:

```bash
vdi log clean
```

Delete one log:

```bash
vdi log clean --pid 43944
```

Cleanup respects `--log-dir`, `--log-prefix`, `VDI_LOG_DIR`, and
`VDI_LOG_FILE_PREFIX`.

## Log format

Each event is represented by one space-delimited line. Dynamic values such as
paths, usernames, hostnames, arguments, and function arguments are
percent-encoded so spaces, control characters, and literal `%` characters remain
unambiguous.

For the complete column-by-column format, see
[wrapper log format](../src/vdi_wrapper/README.md#format-of-the-log-file-line).

## Wrapper diagnostics and writes

The wrapper supports two additional environment settings:

| Setting | Default | Meaning |
|---------|---------|---------|
| `VDI_LOG_DEBUG_LEVEL` | `0` | Level of diagnostic output (`0`–`4`) |
| `VDI_LOG_MIN_WRITE_BYTES` | `1` | Minimum non-zero logged write size |

Writes below `VDI_LOG_MIN_WRITE_BYTES` still occur, but they are not logged.
Invalid or non-positive thresholds are ignored.
