# VDI client

The VDI client provides the `vdi` command for using the virtual data
infrastructure (VDI). It can run programs with file-I/O instrumentation and
transparent remote-file downloads, manage views on a VDI server, and inspect
the logs produced by instrumented runs.

## What the package contains

Each published wheel contains the `vdi` command, its Python implementation, and
native wrapper libraries for the wheel's Linux architecture. The libraries are
built per supported EESSI version and named, for example,
`libvdi_eessi2025.06.so`. At runtime, `vdi run` selects the library matching
the active EESSI version.

## Installation

Initialize EESSI, create a virtual environment using its compatibility-layer
Python, and install the package:

```bash
source /cvmfs/software.eessi.io/versions/2025.06/init/bash
"${EESSI_EPREFIX}/usr/bin/python" -m venv ~/.venvs/vdi-client
source ~/.venvs/vdi-client/bin/activate
python -m pip install vdi-client
```

Only `vdi run` loads a native wrapper library. Other commands, such as
`vdi view`, do not require one.

## Usage

Check the installed version and available commands:

```bash
vdi --version
vdi --help
```

Configure a VDI server once:

```bash
mkdir -p ~/.vdi
echo 'BASE_URL=https://vdi.example.org' > ~/.vdi/config
```

List views on the configured server:

```bash
vdi view list
```

Run a command with VDI instrumentation:

```bash
vdi run python my_script.py input.dat --output results/
```

Inspect generated log files:

```bash
vdi log list
vdi log show <pid>
```

### Examples

- Dry-run a wrapped command: `vdi run --dry-run python my_script.py`
- Override the server for one call:
  `vdi view --base-url https://vdi.example.org list`
- Use a custom configuration file: `vdi view --config ~/vdi-test.conf list`
- Preview log cleanup: `vdi log clean --dry-run`

More detailed examples are part of the
[rendered VDI documentation](https://virtual-data-infrastructure.github.io/vdi-docs/).

## Views and caching

The current `vdi view` commands operate directly against the configured VDI
server. They do not cache server responses locally or provide offline operation.

## Links

- [VDI documentation](https://virtual-data-infrastructure.github.io/vdi-docs/)
- [Client guide](https://virtual-data-infrastructure.github.io/vdi-docs/)
- [Source code](https://github.com/virtual-data-infrastructure/vdi-client)
- [Issue tracker](https://github.com/virtual-data-infrastructure/vdi-client/issues)

## License

GPL-2.0-only. See [LICENSE](LICENSE) for details.
