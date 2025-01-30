# VDI client

This repository contains client tools for the virtual data infrastructure:

- the script `vdi` which can be used to perform several actions such as running
  a program with the extensions to implement the VDI
- the source code and Makefile to compile, link and install the shared library
  `libvdi.so` that provides the extensions
- a Makefile to install the script `vdi`

# Prerequisites
- Mount the EESSI software repository at `/cvmfs/software.eessi.io` (see
  [Installation and configuration](https://www.eessi.io/docs/getting_access/is_eessi_accessible/)).
- Initialize EESSI by running the command
  ```bash
  source /cvmfs/software.eessi.io/versions/2023.06/init/bash
  ```
  For alternative initializations, see [Set up environment](https://www.eessi.io/docs/using_eessi/setting_up_environment/)

# Installation
- Clone the code into a local directory and run `make all` in the main directory
  of the repository.
- Add the directory that contains the installed script `vdi` to the `$PATH`
  environment variable. Note, make sure that the script is findable in new
  shell sessions and, particularly, in job scripts.

# Using the `vdi` script
Simply run the script `vdi -h` or `vdi` to obtain an overview of its arguments
as shown below
```
Usage: vdi [commands] [common arguments] [cmd specific arguments]
  Commands:
    run            - run the user program with the given user arguments
    view           - create, list and delete views
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
installed in `lib64/`, see [wrapper README](src/vdi_wrapper/README.md)

# Example: `map_plot.py`

Load `geopandas`
```
module load geopandas/0.14.2-foss-2023a
```
Run example with
```
vdi run python examples/map_plot.py data/no.json --out outputs
```
which creates the PNG-file `outputs/no.json_map.png`. The run will also print
a message like
```
vdi.so: using log file '/home/almalinux/.vdi/logs/vdi_log.43944.log'
```
In this case, the log shows lots of `openat` calls for opening `.pyc` files
under `/cvmfs/software.eessi.io`. Filtering these out with
```
grep -v "python.* /cvmfs" /home/almalinux/.vdi/logs/vdi_log.43944.log
```
we get the following accesses
```
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
has created such as
```
created PNG-file 'outputs/no.json_map.png'
```

# Additional information about configuration, log file format and debug levels
See [wrapper README](src/vdi_wrapper/README.md) for detailed information.
