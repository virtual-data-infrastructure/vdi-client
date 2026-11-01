# VDI client

The VDI client provides tools for interacting with the virtual data
infrastructure (VDI). It includes:

- the `vdi` command-line client
- the shared library `libvdi.so`, which records file-I/O activity and can
  transparently download files from remote resources while a program runs
- utilities for managing views on a VDI server and inspecting generated logs

## Package contents

In a source checkout, the native wrapper library is called `libvdi.so`. Release
wheels instead bundle EESSI-versioned libraries such as
`libvdi_eessi2025.06.so`. The compatible CPU architecture is identified by the
wheel's platform tag, and the matching library is selected automatically when
`vdi run` starts.

## Requirements

- An initialized EESSI environment. The example below uses EESSI 2025.06;
  published wheels also support other documented EESSI versions.

  ```bash
  source /cvmfs/software.eessi.io/versions/2025.06/init/bash
  ```

- A virtual environment created with the Python provided by the active EESSI
  compatibility layer.

See the [EESSI access documentation](https://www.eessi.io/docs/getting_access/is_eessi_accessible/)
for mounting and initialization options.

## Installation

Create a virtual environment with EESSI's Python and install the published
client from PyPI:

```bash
"${EESSI_EPREFIX}/usr/bin/python" -m venv ~/.venvs/vdi-client
source ~/.venvs/vdi-client/bin/activate
python -m pip install vdi-client
```

For development or use directly from a checkout, build and install the bundled
wrapper library and launcher:

```bash
make all
export PATH="$PWD/bin:$PATH"
```

## Quick start

Preview a wrapped command without executing it:

```bash
vdi run --dry-run python -c 'print("Hello, VDI")'
```

Store the address of your VDI server in `~/.vdi/config`:

```bash
mkdir -p ~/.vdi
echo 'BASE_URL=https://vdi.example.org' > ~/.vdi/config
```

Then list the views available on that server:

```bash
vdi view list
```

Run a program with VDI instrumentation enabled:

```bash
vdi run python examples/map_plot.py data/no.json --out outputs
```

The wrapper prints the path to the generated log file. List and inspect it with:

```bash
vdi log list
vdi log show <pid>
```

## Detailed documentation

- [Configuration](docs/configuration.md)
- [Command-line usage](docs/cli.md)
- [Examples](docs/examples.md)
- [Managing VDI logs](docs/logging.md)
- [Wrapper library reference](src/vdi_wrapper/README.md)
- [Development guide](docs/development.md)
- [Release guide](docs/release.md)

Project-level VDI documentation is maintained in the
[rendered VDI documentation](https://virtual-data-infrastructure.github.io/vdi-docs/).
