# Directory for code employing `$LD_PRELOAD` to collect (data) traces
Employing `$LD_PRELOAD` will enable using the tools / libraries for augmenting or changing existing functionality to collect data traces. The main purpose of employing `$LD_PRELOAD` is to have a quick path towards playing with augmenting existing system calls such as `open` or `execve`.

Advantages:
- Can be used with existing systems.
- Good for development of envisioned features.

Disadvantages:
- Must be explicitly used, i.e., tracing functionality is not provided transparently.
- `$LD_PRELOAD` may have undesired consequences leading to program crashes, unresolved libraries/symbols, or conflicts.

## Building the wrapper library
Make sure to use the `gcc` from the compatibulity layer. Run `which gcc`, which should print something like
```
/cvmfs/software.eessi.io/versions/2023.06/compat/linux/x86_64/usr/bin/gcc
```
Build the wrapper library `libvdi_logger.so` with
```
gcc -fPIC -shared -o libvdi_logger.so vdi_logger.c -ldl -Wall -Wextra -Werror -g
```
## Using the wrapper library
Simply set `LD_PRELOAD=libvdi_logger.so` before running a program. For some Python examples provided in the `examples` directory, load the necessary modules and run some tests

### Example: `map_plot.py`

Load `geopandas`
```
module load geopandas/0.14.2-foss-2023a
```
Run example
```
LD_PRELOAD=libvdi_logger.so python examples/map_plot.py data/no.json --out outputs
```
which creates the PNG-file `outputs/no.json_map.png`. The run will also print a message like
```
vdi_logger.so: using log file '/home/almalinux/.vdi/logs/vdi_log.43944'
```
In this case, the log shows lots of `openat` calls for opening `.pyc` files under `/cvmfs/software.eessi.io`. Filtering these out with
```
grep -v cvmfs /home/almalinux/.vdi/logs/vdi_log.43944
```
we get the following accesses
```
open64 /home/almalinux/data-graph/src/ld-preload/examples/map_plot.py 524288::O_RDONLY 438::0666
open64 /usr/share/zoneinfo/UTC 524288::O_RDONLY 438::0666
open64 /home/almalinux/.cache/matplotlib/fontlist-v330.json 524288::O_RDONLY 438::0666
fopen /home/almalinux/.local/share/proj/proj.ini rb
fopen /home/almalinux/.local/share/proj/proj.db rb
open64 data/no.json_map.png 524866::O_RDONLY+O_RDWR+O_CREAT+O_TRUNC 438::0666
```
The Python script `map_plot.py` also prints a message about the image file it has created such as
```
created PNG-file 'outputs/no.json_map.png'
```
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
| 12 | Name of the intercepted function |
| 13+ | Arguments of the intercepted function such as the accessed `path`, the flags to open a file, the mode to open a file, etc |

### Configuring log file path and name
The log file always contains the process ID as suffix, is by default written into the directory `${HOME}/.vdi/logs/` and has the prefix/name `vdi_log.`.

Both the directory and the prefix/name can be configured with the environment variables `$VDI_LOG_DIR` and `$VDI_LOG_FILE_PREFIX`, respectively. For example,
```
export VDI_LOG_DIR=/tmp
export VDI_LOG_FILE_PREFIX='vdi_log_${USER}.'
LD_PRELOAD=libvdi_logger.so python examples/map_plot.py data/no.json --out outputs
```
will print the messages
```
vdi_logger.so: using log file '/tmp/vdi_log_almalinux.43948'
created PNG-file 'outputs/no.json_map.png'
```
