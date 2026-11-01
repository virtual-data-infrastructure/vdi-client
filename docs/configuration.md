# Configuration

The `vdi` client separates command-line settings from runtime settings used by
the native wrapper library. This page describes both, with special attention to
the optional CLI configuration file.

## CLI configuration file

By default, the CLI reads `~/.vdi/config` when it starts. The file is optional;
if it does not exist, the CLI continues without configuration values.

There is currently no environment variable for the configuration-file location.
Use `--config` for directory-specific or alternative setups, including those
managed with `direnv`.

### Syntax

The file contains one `KEY=VALUE` assignment per line:

```bash
# Address of the VDI server.
BASE_URL=https://vdi.example.org
```

Blank lines and lines beginning with `#` are ignored. Surrounding whitespace is
stripped, and one pair of matching single or double quotes around a value is
removed:

```bash
BASE_URL="https://vdi.example.org"
OTHER_VALUE='literal text'
```

Lines without `=` are silently ignored. If a key appears more than once, the
last assignment wins.

The parser is intentionally simple and does not execute shell syntax. Variable
expansion, command substitution, sourcing, and arbitrary shell expressions are
not supported.

### Recognized settings

Currently, the CLI consumes only `BASE_URL`. Unknown keys are retained in memory
by the parser but are not used by this version of the client. They may be given
meaning in a future release, but they should not be relied upon until documented.

The server environment variable is also unprefixed (`BASE_URL`). A future
release may introduce `VDI_BASE_URL` for consistency, but backward compatibility
would need to be preserved.

### Choosing a configuration file

Use `--config` to select another file for a single invocation:

```bash
vdi view --config ~/vdi-production.conf list
```

The option is accepted by `run`, `view`, and `log`. Paths may be relative or
absolute.

## Base URL precedence

The VDI server base URL is resolved in this order:

1. `--base-url` command-line option
2. `BASE_URL` in the selected configuration file
3. the `BASE_URL` environment variable

For example, a value supplied with `--base-url` always takes precedence, while
a value in the config file takes precedence over an inherited environment
variable.

```bash
BASE_URL=https://fallback.example.org \
  vdi view --base-url https://override.example.org list
```

## Wrapper runtime settings

The native wrapper library reads these values from the environment of the
process launched by `vdi run`. Consequently, they are not read from
`~/.vdi/config` in the current release. Supporting them there would require
`vdi run` to translate configured values into environment variables before
starting the wrapped program.

- `VDI_LOG_DIR`: log directory; default `~/.vdi/logs`; overridden by
  `--log-dir`.
- `VDI_LOG_FILE_PREFIX`: log filename prefix; default `vdi_log.`; overridden by
  `--log-prefix`.
- `VDI_LIB_PATH`: explicit wrapper-library path; overridden by `--lib`.
  Without either setting, the client selects a bundled library automatically.
- `VDI_LOG_DEBUG_LEVEL`: wrapper diagnostic verbosity from `0` through `4`;
  default `0`.
- `VDI_LOG_MIN_WRITE_BYTES`: number of bytes a write must transfer before it is
  recorded; default `1`.

For `--log-dir`, `--log-prefix`, and `--lib`, the explicit CLI option has the
highest precedence, followed by the environment variable and then the built-in
default.

The source checkout additionally falls back to `lib64/libvdi.so` when no bundled
package library is found.

`VDI_LOG_MIN_WRITE_BYTES` controls log noise, not program behavior. Smaller
values record more small writes; larger values omit short writes from the log.
All writes are still performed. Invalid and non-positive values are ignored.
