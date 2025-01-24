# Directory for the shared wrapper library `libvdi.so` that implements the VDI extensions to EESSI

Technically, the library is loaded via `$LD_PRELOAD` to enable using the tools / libraries for augmenting or changing existing functionality to collect data traces and other capabilities of the _virtual data infrastructure_. The main purpose of employing `$LD_PRELOAD` is to have a quick path towards experimenting with augmenting existing system calls such as `open` or `execve`.

Advantages:
- Can be used with existing systems.
- Good for development of envisioned features.

Disadvantages:
- Must be explicitly used, i.e., tracing functionality is not provided transparently.
- `$LD_PRELOAD` may have undesired consequences leading to program crashes, unresolved libraries/symbols, or conflicts.

## Building the wrapper library
Simply run `make all` and/or `make install`. The `Makefile` checks whether EESSI is initialized and whether the compiler from the compatibility layer in EESSI will be used. If either check fails, the `Makefile` exits and prints some guidance to resolve the issue.

## Using the wrapper library
The wrapper library can be used by setting `LD_PRELOAD` to the path of the library (either `${PWD}/build/libvdi.so` or `${PWD}/../../lib64/libvdi.so`) before running any command. A more comfortable means is provided by the script `vdi` that is provided in the main directory of this repository. After running `make install` in the main directory the script will be installed in the `bin` directory. For more information on using the script see [main README](../../README.md)

### Format of the log file line

| Column | Description |
|--------|-------------|
| 1 | Timestamp (epoch::human-readable-in-UTC) |
| 2 | Hostname, (possibly) fully qualified hostname, IPv4/v6 addresses with main elements being separated by `//` and IP address details separated by `%%` |
| 3 | User name |
| 4 | User `$HOME` |
| 5 | Process ID |
| 6 | Parent process ID |
| 7 | Process group ID |
| 8 | Current working directory |
| 9 | Full path to the program being run |
| 10 | All command line arguments to program (including program name as used on command line). Arguments are separated by `%%`. Whitespaces ('` `' and '`\t`') in arguments are replaced by `##`. |
| 11 | Start time of the program given as epoch and UTC time with the format `EPOCH_TIME%%UTC_TIME`. |
| 12 | Elapsed time (microseconds) since the start time of the program. |
| 13 | Name of the intercepted function |
| 14+ | Arguments of the intercepted function such as the accessed `path`, the flags to open a file, the mode to open a file, etc |

### Configuring log file path and name
The log file always contains the process ID as suffix, is by default written into the directory `${HOME}/.vdi/logs/` and has the prefix/name `vdi_log.`.

Both the directory and the prefix/name can be configured with the environment variables `$VDI_LOG_DIR` and `$VDI_LOG_FILE_PREFIX`, respectively. For example,
```
export VDI_LOG_DIR=/tmp
export VDI_LOG_FILE_PREFIX='vdi_log_${USER}.'
vdi run python examples/map_plot.py data/no.json --out outputs
```
will print the messages
```
vdi_logger.so: using log file '/tmp/vdi_log_almalinux.43948.log'
created PNG-file 'outputs/no.json_map.png'
```

### Configuring debug information
To obtain any output about the processing of the logger the environment variable `VDI_LOG_DEBUG_LEVEL` may be set. For values and what information will be shown, see the table below. The default debug level is zero (0).
| Debug level | Description |
|-------------|-------------|
| 0 | Default level (variable unset or empty). The logger will print no information. |
| 1 | The path to the log file will be printed. |
| 2 | Information about the loading and unloading of the vdi_logger.so shared library and level 1 will be printed. |
| 3 | Information about intercepted calls and levels 1-2 will be printed. |
| 4 | Information about runtime errors and processing details of the logger and levels 1-3 will be printed. |
