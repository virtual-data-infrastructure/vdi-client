# VDI client

This repository contains client tools for the virtual data infrastructure:

- the script `vdi` which can be used to perform several actions such as running a program with the extensions to implement the VDI
- the source code and Makefile to compile, link and install the shared library `libvdi.so` that provides the extensions
- a Makefile to install the script `vdi`

# Prerquisites
- Mount the EESSI software repository at `/cvmfs/software.eessi.io` (see [Installation and configuration](https://www.eessi.io/docs/getting_access/is_eessi_accessible/)).
- Initialize EESSI by running the command
  ```bash
  source /cvmfs/software.eessi.io/versions/2023.06/init/bash
  ```
  For alternative initializations, see [Set up environment](https://www.eessi.io/docs/using_eessi/setting_up_environment/)

# Installation
- Clone the code into a local directory and run `make install` in the main directory of repository.
- Add the directory that contains the installed script `vdi` to the `$PATH` environment variable. Note, make sure that the script is findable in new shell sessions and, particularly, in job scripts.

# Using the `vdi` script
Simply run the script `vdi -h` or `vdi` to obtain an overview of its arguments as shown below
```
Usage: vdi [commands] [common arguments] [cmd specific arguments]
  Commands:
    run            - run the user program with the given user arguments
  Common arguments:
    -h             - print this usage information
    -v             - verbose output
    --dry-run      - only print what command would do without actually performing the actions
  Arguments for command 'run':
    program        - path to program to be run
    program_args   - any arguments to the program to be run
```
For additional configuration settings of the wrapper library `libvdi.so` installed in `lib64/`, see [wrapper README](src/vdi_wrapper/README.md)
