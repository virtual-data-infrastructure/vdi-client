# VDI client

This repository contains client tools for the virtual data infrastructure:

- the script `vdi` which can be used to perform several actions such as running
  a program with the extensions to implement the VDI
- the source code and Makefile to compile, link and install the shared library
  `libvdi.so` that provides the extensions
- a Makefile to install the script `vdi`

## Prerequisites

- Mount the EESSI software repository at `/cvmfs/software.eessi.io` (see
  [Installation and configuration](https://www.eessi.io/docs/getting_access/is_eessi_accessible/)).
- Initialize EESSI by running the command

  ```bash
  source /cvmfs/software.eessi.io/versions/2023.06/init/bash
  ```

  For alternative initializations, see
  [Set up environment](https://www.eessi.io/docs/using_eessi/setting_up_environment/)

## Installation

- Clone the code into a local directory and run `make all` in the main directory
  of the repository.
- Add the directory that contains the installed script `vdi` to the `$PATH`
  environment variable. Note, make sure that the script is findable in new
  shell sessions and, particularly, in job scripts.

## Using the `vdi` script

Simply run the script `vdi -h` or `vdi` to obtain an overview of its arguments
as shown below:

```text
Usage: vdi [commands] [common arguments] [cmd specific arguments]
  Commands:
    run            - run the user program with the given user arguments
    view           - create, list and delete views
    log            - list, show and clean up VDI log files
  Common arguments:
    --base-url     - base url for VDI server to be accessed
    --config       - full path to config file [default: ${HOME}/.vdi/config]
    -h             - print usage for command
    -v             - verbose output
    --dry-run      - only print what command would do without actually performing the actions
  Arguments for command 'run': PROGRAM [PROGRAM_ARGS]
    PROGRAM        - path to program to be run
    PROGRAM_ARGS   - any arguments to the program to be run
  Arguments for command 'view': SUB_COMMAND [SUB_COMMAND_ARGS]
    SUB_COMMAND    - one of 'create', 'delete', 'files', 'geturl', 'list', 'remove' and 'upload'
    Run 'vdi view' for detailed usage information.
```

For additional configuration settings of the wrapper library `libvdi.so`
installed in `lib64/`, see [wrapper README](src/vdi_wrapper/README.md).

## Example: `map_plot.py`

Load `geopandas`:

```bash
module load geopandas/0.14.2-foss-2023a
```

Run example with:

```bash
vdi run python examples/map_plot.py data/no.json --out outputs
```

which creates the PNG-file `outputs/no.json_map.png`. The run will also print a
message like:

```text
vdi.so: using log file '/home/almalinux/.vdi/logs/vdi_log.43944.log'
```

In this case, the log shows lots of `openat` calls for opening `.pyc` files
under `/cvmfs/software.eessi.io`. Filtering these out with:

```bash
grep -v "python.* /cvmfs" /home/almalinux/.vdi/logs/vdi_log.43944.log
```

we get the following accesses:

```text
1736344161::2025-01-08+13:49:21+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 39057 open64 /home/almalinux/data-graph/src/ld-preload/examples/map_plot.py 524288::O_RDONLY 438::0666
1736344161::2025-01-08+13:49:21+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 39648 fopen64 /home/almalinux/data-graph/src/ld-preload/examples/map_plot.py rb
1736344161::2025-01-08+13:49:21+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 300142 open64 /usr/share/zoneinfo/UTC 524288::O_RDONLY 438::0666
1736344162::2025-01-08+13:49:22+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 939529 open64 /home/almalinux/.cache/matplotlib/fontlist-v330.json 524288::O_RDONLY 438::0666
1736344162::2025-01-08+13:49:22+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 1249633 fopen /home/almalinux/.local/share/proj/proj.ini rb
1736344162::2025-01-08+13:49:22+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 1251107 fopen /home/almalinux/.local/share/proj/proj.db rb
1736344162::2025-01-08+13:49:22+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 1261552 fopen64 /home/almalinux/.gdal/gdalrc rb
1736344162::2025-01-08+13:49:22+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 1301996 fopen64 data/no.json rb
1736344162::2025-01-08+13:49:22+UTC nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1//IPv4%%eth0%%158.39.77.38//IPv6%%lo%%::1//IPv6%%eth0%%2001:700:2:8300::2079//IPv6%%eth0%%fe80::f816:3eff:fe4a:c151%eth0 almalinux /home/almalinux 55715 18260 55715 /home/almalinux/data-graph/src/ld-preload /cvmfs/software.eessi.io/versions/2023.06/software/linux/x86_64/intel/haswell/software/Python/3.11.3-GCCcore-12.3.0/bin/python3.11 python%%examples/map_plot.py%%data/no.json%%--out%%outputs 1736344160%%2025-01-08+13:49:20+UTC 1477680 open64 outputs/no.json_map.png 524866::O_RDONLY+O_RDWR+O_CREAT+O_TRUNC 438::0666
```

The Python script `map_plot.py` also prints a message about the image file it
has created such as:

```text
created PNG-file 'outputs/no.json_map.png'
```

## Additional information about configuration, log file format and debug levels

See [wrapper README](src/vdi_wrapper/README.md) for detailed information.

## Managing log files

The `vdi log` subcommand provides tools to list, inspect and clean up the log
files created by `libvdi.so` during `vdi run` sessions. Log files are stored in
the directory defined by `$VDI_LOG_DIR` (default: `~/.vdi/logs/`) and use the
naming convention `vdi_log.<pid>.log` (the prefix can be changed via
`$VDI_LOG_FILE_PREFIX`).

### Listing log files

```bash
vdi log list
```

By default, this prints a short listing (PID and file name). Use `--long` for
additional details (size, modification time and program name):

```bash
vdi log list --long
```

Sort options (`--sort`) and reverse (`-r`/`--reverse`) are available:

```bash
vdi log list --sort size --reverse
vdi log list --sort date
vdi log list --sort program
```

### Showing a log file

```bash
vdi log show <pid>
```

Prints the contents of `vdi_log.<pid>.log` to stdout.

### Cleaning up log files

Remove all log files:

```bash
vdi log clean
```

Remove a specific log file by PID:

```bash
vdi log clean --pid <pid>
```

Both commands support `--dry-run` to preview what would be removed.

### Overriding the log directory and prefix

All `vdi log` subcommands accept `--log-dir` and `--log-prefix` to override the
defaults (or the corresponding environment variables) for a single invocation:

```bash
vdi log --log-dir /tmp/my-logs --log-prefix 'vdi_log_user.' list
```

## Development

### Setting up a development environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running the CLI

```bash
vdi --version                              # print version
vdi                                        # print help
vdi run --dry-run ls -la                   # dry-run: show what would be executed
vdi run --lib /path/to/libvdi.so python    # run a program with VDI extensions
vdi view --base-url http://localhost list  # list all views on the server
vdi view --base-url http://localhost create myview  # create a new view
```

### Running tests

```bash
pytest
```

### Linting and type checking

```bash
ruff check
ruff format --check
mypy
pyright
codespell
pymarkdown -c .pymarkdown.json scan README.md src/vdi_wrapper/README.md
```

### Building a wheel

The `make build-wheel` target compiles `libvdi.so` under EESSI, copies it
into `vdi_client/lib/`, and builds a platform wheel that bundles the shared
library.

```bash
# EESSI must be initialized and the environment must be clean
# (no LD_LIBRARY_PATH, LIBRARY_PATH scoped to EESSI)
make build-wheel
```

If the `build` package is not available, `make build-wheel` automatically
creates a temporary virtual environment, installs `build` into it, builds
the wheel, and removes the venv.

To use a persistent virtual environment (e.g. for debugging or repeated
builds), create one manually:

```bash
# Create and activate a venv using the EESSI compat-layer Python
$EESSI_EPREFIX/usr/bin/python -m venv .build-venv
source .build-venv/bin/activate
pip install --upgrade pip
pip install build

# Build the wheel
make build-wheel

# Clean up when done
deactivate
make clean-wheel
```

The resulting wheel is written to `dist/`.

### Releasing

Releases are triggered by pushing a tag matching `v*` (e.g. `v0.1.0`).
The GitHub Actions workflow in `.github/workflows/release.yml` then builds
a platform wheel (compiling `libvdi.so` against EESSI) and publishes it to
PyPI using OIDC trusted publishing - no API token is stored as a secret.

#### One-time setup: PyPI trusted publishing

Before the first release, a project maintainer must configure the
connection between GitHub and PyPI:

##### Log in to PyPI

- Go to <https://pypi.org> and log in.

##### Add the trusted publisher

- Navigate to **Your account** -> **Publishing**
- Scroll down to section **Add a new pending publisher**
- Fill in the GitHub tab:
  - **PyPI project name**: `vdi-client`
  - **Owner**: `virtual-data-infrastructure`
  - **Repository**: `vdi-client`
  - **Workflow filename**: `release.yml`
  - **Environment name**: `pypi`

##### Create the `pypi` environment on GitHub

- Go to the repository **Settings** -> **Environments** -> **New environment**.
- Name it `pypi`.
- (Optional) Add required reviewers so a human must approve the
  publish job before it runs.

No API tokens or secrets are needed. Authentication is handled entirely
through the OIDC token exchange between GitHub Actions and PyPI.

#### Creating a release

```bash
git checkout main
git pull origin main
git tag v0.1.0
git push origin v0.1.0
```

The release workflow will:

1. Build a platform wheel for each architecture in the matrix
   (currently `x86_64`; `aarch64` and `riscv64` can be added later).
2. Publish all wheels to PyPI under the `pypi` environment.

After the workflow completes, the new version is installable via
`pip install vdi-client` or `uv pip install vdi-client`.
