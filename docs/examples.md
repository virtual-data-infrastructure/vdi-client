# Examples

This page contains only a small set of examples that are closely tied to the
client repository. Broader usage guides and workflows belong in the
[rendered VDI documentation](https://virtual-data-infrastructure.github.io/vdi-docs/).

## Configure a server

```bash
mkdir -p ~/.vdi
echo 'BASE_URL=https://vdi.example.org' > ~/.vdi/config
vdi view list
```

Use `--base-url` for a single connection to another server:

```bash
vdi view --base-url https://staging.vdi.example.org list
```

## Preview an instrumented run

```bash
vdi run --dry-run python -c 'print("Hello, VDI")'
```

Nothing is executed, and no log file is created.

## Run the bundled map example

With EESSI initialized and a compatible Python environment active:

```bash
module load geopandas/0.14.2-foss-2023a
vdi run python examples/map_plot.py data/no.json --out outputs
```

Expected output resembles:

```text
vdi.so: using log file '/home/example-user/.vdi/logs/vdi_log.43944.log'
created PNG-file 'outputs/no.json_map.png'
```

## Inspect the resulting log

Use the PID from the preceding `vdi run` output:

```bash
vdi log show 43944
```

For a broader overview:

```bash
vdi log list --all --long
```

See [log format](../src/vdi_wrapper/README.md#format-of-the-log-file-line) for
column meanings and percent encoding.
