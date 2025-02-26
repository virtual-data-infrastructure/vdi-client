#include <arpa/inet.h>
#include <ctype.h>
#include <curl/curl.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <ifaddrs.h>
#include <limits.h>
#include <netdb.h>
#include <pwd.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/sysinfo.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

bool _global_show_log_path = true;
int _global_debug_level = 0;

const int MAX_BUFFER_SIZE = 4096;
const int MAX_PATH_LEN = PATH_MAX;
const int MAX_STRING_LEN = 1024;
const int MAX_HOSTNAME_LEN = 256;


const char* STRING_CONST_FCLOSE_FUNCNAME = "fclose";
const char* STRING_CONST_FOPEN64_FUNCNAME = "fopen64";
const char* STRING_CONST_FOPENAT_FUNCNAME = "fopenat";
const char* STRING_CONST_FOPEN_FUNCNAME = "fopen";
const char* STRING_CONST_FREOPEN_FUNCNAME = "freopen";
const char* STRING_CONST_FWRITE_FUNCNAME = "fwrite";
const char* STRING_CONST_OPEN64_FUNCNAME = "open64";
const char* STRING_CONST_OPENAT_FUNCNAME = "openat";
const char* STRING_CONST_OPEN_FUNCNAME = "open";
const char* STRING_CONST_WRITE_FUNCNAME = "write";

const char* STRING_CONST_LOG_COLUMN_SEPARATOR = " ";
const char* STRING_CONST_LOG_NEW_LINE = "\n";
const char* STRING_CONST_ENVVAR_VDI_LOG_DIR = "VDI_LOG_DIR";
const char* STRING_CONST_ENVVAR_DEFAULT_VDI_LOG_DIR = "${HOME}/.vdi/logs";
const char* STRING_CONST_ENVVAR_VDI_LOG_FILE_PREFIX = "VDI_LOG_FILE_PREFIX";
const char* STRING_CONST_ENVVAR_DEFAULT_VDI_LOG_FILE_PREFIX = "vdi_log.";
const char* STRING_CONST_ENVVAR_VDI_LOG_DEBUG_LEVEL = "VDI_LOG_DEBUG_LEVEL";
const char* STRING_CONST_UTC_ERROR = "UTC_ERROR";
const char* STRING_CONST_READLINK_ERROR = "READLINK_ERROR";
const char* STRING_CONST_PROGRAM_ARGS_ERROR = "PROGRAM_ARGS_ERROR";
const char* STRING_CONST_GETCWD_ERROR = "GETCWD_ERROR";
const char* STRING_CONST_USERNAME_ERROR = "USERNAME_ERROR";
const char* STRING_CONST_USERHOME_ERROR = "USERHOME_ERROR";
const char* STRING_CONST_HOSTNAME_ERROR = "HOSTNAME_ERROR";
const char* STRING_CONST_FQHN_ERROR = "FQHN_ERROR";
const char* STRING_CONST_FQHN_NOT_RESOLVED_ERROR = "FQHN_NOT_RESOLVED_ERROR";
const char* STRING_CONST_IP_ADDRESS_ERROR = "IP_ADDRESS_ERROR";
const char* STRING_CONST_PROGRAM_START_TIME_ERROR = "PROGRAM_START_TIME_ERROR";
const char* STRING_CONST_PROGRAM_ELAPSED_TIME_ERROR = "PROGRAM_ELAPSED_TIME_ERROR";
const char* STRING_CONST_PROGRAM_ARG_SEPARATOR = "%%";
const char* STRING_CONST_PROGRAM_ARG_WHITESPACE_SUBSTITUTE = "##";
const char* STRING_CONST_FQHN_AND_IP_SEPARATOR = "//";
const char* STRING_CONST_IPVER_SEPARATOR = "%%";
const char* STRING_CONST_PROGRAM_STARTTIME_SEPARATOR = "%%";
const char* STRING_CONST_DIRECTORY_SEPARATOR = "/";
const char* STRING_CONST_VDI_DEBUG_PREFIX = "vdi.so: ";
const char* STRING_CONST_ENVVAR_VDI_DOWNLOAD_BASE = "VDI_DOWNLOAD_BASE";
const char* STRING_CONST_DOWNLOAD_BASE_DEFAULT = "/tmp/%s/vdi/downloads"; // replace with $USER
const char* STRING_CONST_DOWNLOAD_FILENAME_TEMPLATE = "%d.%d.%s"; // $$.EPOCH.filename_from_url
const char* STRING_CONST_DOWNLOAD_FILENAME_DEFAULT = "default_filename";

const char *URL_PREFIXES[] = {
  "https://",
  "http://",
  "ftp://"
};
size_t NUM_URL_PREFIXES = sizeof(URL_PREFIXES) / sizeof(URL_PREFIXES[0]);

// functions we use in here but that are also wrapped
int (*actual_fclose)() = NULL;
FILE* (*actual_fopen64)() = NULL;
FILE* (*actual_fopenat)() = NULL;
FILE* (*actual_fopen)() = NULL;
FILE* (*actual_freopen)() = NULL;
size_t (*actual_fwrite)() = NULL;
int (*actual_open64)() = NULL;
int (*actual_openat)() = NULL;
int (*actual_open)() = NULL;
int (*actual_write)() = NULL;

// debug function
void debug(int debug_level, const char* format, ...) {
    if (debug_level <= _global_debug_level) {
        va_list args;
        va_start(args, format);

        // prepare pid string to add to debug output after prefix
        char pid_string[32];
        pid_t pid = getpid();
        snprintf(pid_string, sizeof(pid_string), "[pid %d] ", pid);

        int string_length = strlen(STRING_CONST_VDI_DEBUG_PREFIX)+strlen(pid_string)+strlen(format)+1;
        char *format_with_prefix = (char *)malloc(string_length * sizeof(char));
        format_with_prefix[0] = '\0';
        strcat(format_with_prefix, STRING_CONST_VDI_DEBUG_PREFIX);
        strcat(format_with_prefix, pid_string);
        strcat(format_with_prefix, format);
        vfprintf(stderr, format_with_prefix, args);
        va_end(args);
        free(format_with_prefix);
    }
}

// constructor function
__attribute__((constructor))
void library_load(void) {
    char *value = getenv(STRING_CONST_ENVVAR_VDI_LOG_DEBUG_LEVEL);
    if (value) {
        _global_debug_level = atoi(value);
    }
    debug(2, "Shared Library Loaded: library_load() called\n");

    // obtain pointers to actual functions
    if (actual_fclose == NULL) {
      actual_fclose = dlsym(RTLD_NEXT, STRING_CONST_FCLOSE_FUNCNAME);
    }
    if (actual_fopen64 == NULL) {
      actual_fopen64 = dlsym(RTLD_NEXT, STRING_CONST_FOPEN64_FUNCNAME);
    }
    if (actual_fopenat == NULL) {
      actual_fopenat = dlsym(RTLD_NEXT, STRING_CONST_FOPENAT_FUNCNAME);
    }
    if (actual_fopen == NULL) {
      actual_fopen = dlsym(RTLD_NEXT, STRING_CONST_FOPEN_FUNCNAME);
    }
    if (actual_freopen == NULL) {
      actual_freopen = dlsym(RTLD_NEXT, STRING_CONST_FREOPEN_FUNCNAME);
    }
    if (actual_fwrite == NULL) {
      actual_fwrite = dlsym(RTLD_NEXT, STRING_CONST_FWRITE_FUNCNAME);
    }
    if (actual_write == NULL) {
      actual_write = dlsym(RTLD_NEXT, STRING_CONST_WRITE_FUNCNAME);
    }
    if (actual_open64 == NULL) {
        actual_open64 = dlsym(RTLD_NEXT, STRING_CONST_OPEN64_FUNCNAME);
    }
    if (actual_openat == NULL) {
        actual_openat = dlsym(RTLD_NEXT, STRING_CONST_OPENAT_FUNCNAME);
    }
    if (actual_open == NULL) {
        actual_open = dlsym(RTLD_NEXT, STRING_CONST_OPEN_FUNCNAME);
    }
}

// destructor function
__attribute__((destructor))
void library_unload(void) {
    debug(2, "Shared Library Unloaded: library_unload() called\n");
}

// helper functions
void convert_ticks_to_epoch_and_utc(long long start_time_ticks, int *epoch_time, char *utc_time, size_t size) {
    long ticks_per_second = sysconf(_SC_CLK_TCK);
    if (ticks_per_second <= 0) {
        strcat(utc_time, STRING_CONST_PROGRAM_START_TIME_ERROR);
        *epoch_time = -1;
        return;
    }

    struct sysinfo info;
    if (sysinfo(&info) == -1) {
        strcat(utc_time, STRING_CONST_PROGRAM_START_TIME_ERROR);
        *epoch_time = -1;
        return;
    }
    // calculate the process start time in seconds since the Epoch
    time_t start_time_seconds = time(NULL) - info.uptime + (start_time_ticks / ticks_per_second);
    *epoch_time = start_time_seconds;

    // convert to UTC time
    struct tm *start_time_tm = gmtime(&start_time_seconds);
    if (start_time_tm == NULL) {
        strcat(utc_time, STRING_CONST_PROGRAM_START_TIME_ERROR);
        return;
    }

    strftime(utc_time, size, "%Y-%m-%d+%H:%M:%S+UTC", start_time_tm);
    return;
}

char** create_array_of_strings(int num_strings, int string_len) {
    char **array = (char **)malloc(num_strings * sizeof(char*));
    for(int i = 0; i < num_strings; i++) {
        array[i] = (char *)malloc(string_len * sizeof(char));
        array[i][0] = '\0';
    }
    return array;
}

int create_dir(const char *pathname) {
    char temp_path[MAX_PATH_LEN];
    strncpy(temp_path, pathname, sizeof(temp_path));
    temp_path[sizeof(temp_path) - 1] = '\0';

    // iterate over each '/' in the pathname
    for (char *p = strchr(temp_path + 1, '/'); p != NULL; p = strchr(p + 1, '/')) {
        *p = '\0';
        struct stat st;
        if (stat(temp_path, &st) != 0) {
            if (mkdir(temp_path, 0700) != 0) {
                perror("mkdir");
                return -1;
            }
        } else if (!S_ISDIR(st.st_mode)) {
            // path exists but is not a directory
            errno = ENOTDIR;
            perror("not a directory");
            return -1;
        }
        *p = '/';
    }

    // Finally, create the full directory path
    struct stat st;
    if (stat(temp_path, &st) != 0) {
        if (mkdir(temp_path, 0700) != 0) {
            perror("mkdir");
            return -1;
        }
    } else if (!S_ISDIR(st.st_mode)) {
        errno = ENOTDIR;
        perror("not a directory");
        return -1;
    }

    return 0;
}

const char *get_filename_from_url(const char *url) {
    const char *slash = strrchr(url, '/');
    if (!slash || strlen(slash + 1) == 0) {
        // return NULL if no slash or no filename after the slash
        return NULL;
    }
    return slash + 1;
}

char* get_directory(char *path) {
    if (path == NULL || *path == '\0') {
        return ".";
    }

    // duplicate the input path to avoid modifying the original
    char *temp_path = strdup(path);
    if (temp_path == NULL) {
        return ".";
    }

    // remove trailing slashes
    char *end = temp_path + strlen(temp_path) - 1;
    while (end > temp_path && *end == '/') {
        *end = '\0';
        end--;
    }

    // find the last slash
    char *last_slash = strrchr(temp_path, '/');

    // handle different cases based on the position of the last slash
    if (last_slash == NULL) {
        // no slash found, return "."
        free(temp_path);
        return ".";
    } else if (last_slash == temp_path) {
        // the last slash is the first character
        *(last_slash + 1) = '\0';
    } else {
        // truncate the path at the last slash
        *last_slash = '\0';
    }

    // duplicate the result to return and free the temporary buffer
    char *result = strdup(temp_path);
    free(temp_path);
    return result;
}

// callback function to write received data to a file (used by curl in function
// download below)
size_t write_data(void *ptr, size_t size, size_t nmemb, FILE *stream) {
  size_t written = actual_fwrite(ptr, size, nmemb, stream);
  return written;
}

// possible error codes:
// EFAULT - bad address
// EACCES - permission denied
// ENAMETOOLONG - file name too long
// ENOENT - no such file or directory
// ENOMEM - out of memory
// ENOSPC - no space left on device
int download(const char *url, char **local_path) {
  // default local download location: /tmp/$USER/vdi/downloads/$$.EPOCH.filename_from_url
  // if env var VDI_DOWNLOAD_BASE is set, use $VDI_DOWNLOAD_BASE/$$.EPOCH.filename_from_url
  // STRING_CONST_DOWNLOAD_BASE_DEFAULT = "/tmp/%s/vdi/downloads"; // replace with $USER
  // STRING_CONST_DOWNLOAD_FILENAME_TEMPLATE = "%d.%d.%s"; // $$.EPOCH.filename_from_url
  // TODO if local_path is initialized use that as path to store file (need to check
  //   whether it exists, so then also need flags/mode from open call

  // determine download base dir
  char *download_base = getenv(STRING_CONST_ENVVAR_VDI_DOWNLOAD_BASE);
  if (download_base == NULL) {
    char *username = NULL;
    uid_t uid = getuid();
    // get the password record for the current user
    struct passwd *pw = getpwuid(uid);
    if (pw == NULL) {
        username = strdup(STRING_CONST_USERNAME_ERROR);
    } else {
        username = pw->pw_name;
    }
    char path[MAX_PATH_LEN];
    snprintf(path, MAX_PATH_LEN-1, STRING_CONST_DOWNLOAD_BASE_DEFAULT, username);
    download_base = strdup(path);
  }
  // determine download filename
  char *local_filename = (char *) get_filename_from_url(url);
  if (local_filename == NULL) {
    // use alternative approach with STRING_CONST_DOWNLOAD_FILENAME_TEMPLATE
    // for which we need the process id, the epoch and a default filename
    char tmp_filename[MAX_PATH_LEN];
    tmp_filename[0] = '\0';
    pid_t pid = getpid();
    time_t epoch = time(NULL);
    snprintf(tmp_filename, MAX_PATH_LEN-1, STRING_CONST_DOWNLOAD_FILENAME_TEMPLATE, pid, epoch, STRING_CONST_DOWNLOAD_FILENAME_DEFAULT);
    local_filename = strdup(tmp_filename);
  }
  char fullpath_local_file[MAX_PATH_LEN];
  fullpath_local_file[0] = '\0';
  strcat(fullpath_local_file, download_base);
  strcat(fullpath_local_file, STRING_CONST_DIRECTORY_SEPARATOR);
  strcat(fullpath_local_file, local_filename);
  *local_path = fullpath_local_file;

  // obtain directory from fullpath_local_file and make sure it exists
  char *fullpath_directory = get_directory(fullpath_local_file);
  if (create_dir(fullpath_directory) != EXIT_SUCCESS) {
    char err_msg[MAX_STRING_LEN];
    snprintf(err_msg, MAX_STRING_LEN, "download dir '%s' does not exist or is not a directory", fullpath_directory);
    perror(err_msg);
    return EXIT_FAILURE;
  }
  debug(4, "created directory '%s' to download '%s'\n", fullpath_directory, fullpath_local_file);

  CURL *curl;
  FILE *fp;
  CURLcode res;

  curl_global_init(CURL_GLOBAL_DEFAULT);
  curl = curl_easy_init();
  if (curl) {
      fp = actual_fopen(fullpath_local_file, "wb");
      int error_code = errno;
      if (fp == NULL) {
          char err_msg[MAX_STRING_LEN];
          snprintf(err_msg, MAX_STRING_LEN, "Failed to open file '%s' for writing", fullpath_local_file);
          perror(err_msg);
          return error_code; // rather use some error code
      }
      
      curl_easy_setopt(curl, CURLOPT_URL, url);
      curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_data);
      curl_easy_setopt(curl, CURLOPT_WRITEDATA, fp);
      // skip automatically following redirects? maybe allow it for idea 2
      curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L); // Follow redirections if necessary

      res = curl_easy_perform(curl);
      if (res != CURLE_OK) {
          fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
          return res; // rather use some error code
      }

      actual_fclose(fp);
      curl_easy_cleanup(curl);
  }
  curl_global_cleanup();

  return 0;
}

char *expand_shell_vars(const char *str) {
    char buffer[MAX_BUFFER_SIZE];
    const char *src = str;
    char *dest = buffer;
    char varname[MAX_BUFFER_SIZE];

    while (*src) {
        if (*src == '$') {
            src++;
            char *var_start = varname;
            if (*src == '{') {
                src++;
                while (*src && *src != '}' && (isalnum((unsigned char)*src) || *src == '_')) {
                    *var_start++ = *src++;
                }
                if (*src == '}') {
                    src++;
                }
            } else {
                while (*src && (isalnum((unsigned char)*src) || *src == '_')) {
                    *var_start++ = *src++;
                }
            }
            *var_start = '\0';

            char *value = getenv(varname);
            if (value) {
                while (*value) {
                    *dest++ = *value++;
                }
            }
        } else {
            *dest++ = *src++;
        }
    }
    *dest = '\0';

    return strdup(buffer);
}

int free_array_of_strings(char **array, int num_strings) {
    if (array == NULL) {
        return EXIT_FAILURE;
    }
    for(int i = 0; i < num_strings; i++) {
        if (array[i] != NULL) {
            free(array[i]);
        }
    }
    free(array);
    return EXIT_SUCCESS;
}

char* get_log_path(void) {
    pid_t pid = getpid();
    char *log_path = (char *)malloc(MAX_PATH_LEN * sizeof(char));
    log_path[0] = '\0';
    char *env_vdi_log_dir = getenv(STRING_CONST_ENVVAR_VDI_LOG_DIR);
    if (env_vdi_log_dir == NULL) {
        // if no directory set use ${HOME}/.vdi/logs
        env_vdi_log_dir = expand_shell_vars(STRING_CONST_ENVVAR_DEFAULT_VDI_LOG_DIR);
    } else {
        env_vdi_log_dir = expand_shell_vars(env_vdi_log_dir);
    }
    char *env_vdi_log_file_prefix = getenv(STRING_CONST_ENVVAR_VDI_LOG_FILE_PREFIX);
    if (env_vdi_log_file_prefix == NULL) {
        env_vdi_log_file_prefix = (char *)STRING_CONST_ENVVAR_DEFAULT_VDI_LOG_FILE_PREFIX;
    } else {
        env_vdi_log_file_prefix = expand_shell_vars(env_vdi_log_file_prefix);
    }

    snprintf(log_path, MAX_PATH_LEN, "%s/%s%d.log", env_vdi_log_dir, env_vdi_log_file_prefix, pid);
    return log_path;
}

long long get_process_start_time(pid_t pid) {
    char path[MAX_BUFFER_SIZE];
    char buffer[MAX_BUFFER_SIZE];
    snprintf(path, sizeof(path), "/proc/%d/stat", pid);

    FILE *file = actual_fopen(path, "r");
    if (file == NULL) {
        return -1;
    } else {
        // read file content
        size_t length = fread(buffer, 1, sizeof(buffer), file);
        fclose(file);
        if (length == 0) {
            return -1;
        } else {
            // extract the 22nd field from the stat file which is the start time
            // Note, the 2nd field begins with '(' and ends with ')'
            buffer[length] = '\0';
            char *ptr = buffer;
            int num = 0;

            while (*ptr != '\0') {
                if (*ptr == '(') {
                    // special field detected
                    char *end = strchr(ptr, ')');
                    if (end == NULL) {
                        // missing ')'
                        num = 0;
                        break;
                    }
                    num++; // increase field counter by one
                    ptr = end + 1; // move past the closing parenthesis
                } else {
                    // regular field
                    num++;
                    char *end = strchr(ptr, ' ');
                    if (end == NULL) {
                        end = ptr + strlen(ptr); // if no space is found, go to end of string
                    } else {
                        if (num == 22) {
                            *end = '\0'; // end column 22 string at found ' '
                            break;
                        } else {
                            ptr = end;
                        }
                    }
                }

                // skip any trailing spaces
                while (*ptr == ' ') {
                    ptr++;
                }
            }
            if (num == 22) {
                // found column 22
                return atoll(ptr);
            } else {
                // something went wrong
                return -1;
            }
        }
    }
}

int log_call(const char *func_name, int func_num_args, char **func_args) {
    char *log_path = get_log_path();
    if (_global_show_log_path) {
        debug(1, "using log file '%s'\n", log_path);
        _global_show_log_path = false;
    }
    char *log_dir = get_directory(log_path);

    if (create_dir(log_dir) != EXIT_SUCCESS) {
        char err_msg[MAX_STRING_LEN];
        snprintf(err_msg, MAX_STRING_LEN, "log dir '%s' does not exist or is not a directory", log_dir);
        perror(err_msg);
        return EXIT_FAILURE;
    }
    int logfd = actual_open(log_path, O_WRONLY | O_CREAT | O_APPEND, 0640);
    if (logfd == -1) {
        // cannot open log_path -> just return for now
        perror("Failed to open file");
        return EXIT_FAILURE;
    }

    // obtain epoch and its representation in UTC where whitespace is replaced with dashes '-'
    time_t current_time = time(NULL);
    char *utc_string;
    if (current_time != (time_t)(-1)) {
        // convert the epoch time to UTC
        struct tm *utc_time = gmtime(&current_time);
        if (utc_time == NULL) {
            utc_string = strdup(STRING_CONST_UTC_ERROR);
        } else {
            // Print the UTC time in a human-readable format
            char utc_buffer[80];
            if (strftime(utc_buffer, sizeof(utc_buffer), "%Y-%m-%d+%H:%M:%S+UTC", utc_time) == 0) {
                utc_string = strdup(STRING_CONST_UTC_ERROR);
            } else {
                utc_string = strdup(utc_buffer);
            }
        }
    } else {
        utc_string = strdup(STRING_CONST_UTC_ERROR);
    }
    char time_string[MAX_STRING_LEN];
    snprintf(time_string, MAX_STRING_LEN-1, "%ld::%s", current_time, utc_string);

    // obtain hostname and IP address(es) {IPv4 + IPv6}
    char hostname[MAX_HOSTNAME_LEN];
    hostname[0] = '\0';
    char *hostname_string = NULL;
    char *fqhn_string = NULL;
    char *ip_string = NULL;
    char ip_string_tmp[MAX_STRING_LEN];
    ip_string_tmp[0] = '\0';
    char *fqhn_and_ip_string = NULL;

    // get the short and fully qualified domain name
    if (gethostname(hostname, sizeof(hostname)) != 0) {
        hostname_string = strdup(STRING_CONST_HOSTNAME_ERROR);
    } else {
        hostname_string = strdup(hostname);
        // get the fully qualified domain name
        struct addrinfo hints, *info, *p;
        int addrinfo_ret, fqhn_ret;

        memset(&hints, 0, sizeof(hints));
        hints.ai_family = AF_UNSPEC;
        hints.ai_socktype = SOCK_STREAM;

        addrinfo_ret = getaddrinfo(hostname, NULL, &hints, &info);
        if (addrinfo_ret != 0) {
            fqhn_string = strdup(STRING_CONST_FQHN_ERROR);
        } else {
            for (p = info; p != NULL; p = p->ai_next) {
                char fqhn_tmp[NI_MAXHOST];
                fqhn_ret = getnameinfo(p->ai_addr, p->ai_addrlen, fqhn_tmp, sizeof(fqhn_tmp),
                                  NULL, 0, NI_NAMEREQD);
                if (fqhn_ret == 0) {
                    fqhn_string = strdup(fqhn_tmp);
                    break;
                }
            }
            freeaddrinfo(info);

            if (p == NULL) {
                fqhn_string = strdup(STRING_CONST_FQHN_NOT_RESOLVED_ERROR);
            }
        }
    }
    // obtain IP addresses
    if (strcmp(hostname_string, hostname) == 0) {
        // we know that we got a hostname
        struct addrinfo hints, *res, *p;
        struct ifaddrs *ifaddr, *ifa;
        char host[NI_MAXHOST];

        int status;
        char ipstr[INET6_ADDRSTRLEN];

        memset(&hints, 0, sizeof(hints));
        hints.ai_family = AF_UNSPEC; // AF_INET or AF_INET6 to force IPv4 or IPv6
        hints.ai_socktype = SOCK_STREAM;

        if (getifaddrs(&ifaddr) != -1) { // try preferred approach
            char buffer[MAX_STRING_LEN];
            buffer[0] = '\0';

            for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
                if (ifa->ifa_addr == NULL)
                    continue;

                int family = ifa->ifa_addr->sa_family;

                if (family == AF_INET || family == AF_INET6) {
                    int s = getnameinfo(ifa->ifa_addr,
                                        (family == AF_INET) ? sizeof(struct sockaddr_in) :
                                                              sizeof(struct sockaddr_in6),
                                        host, NI_MAXHOST,
                                        NULL, 0, NI_NUMERICHOST);
                    if (s != 0) {
                        debug(4, "getnameinfo() failed: %s\n", gai_strerror(s));
                        continue;
                    }

                    snprintf(buffer, MAX_STRING_LEN-1, "%s%s%s%s%s",
                             (family == AF_INET ? "IPv4" : "IPv6"), STRING_CONST_IPVER_SEPARATOR,
                             ifa->ifa_name, STRING_CONST_IPVER_SEPARATOR, host);
                    if (strlen(ip_string_tmp) != 0) {
                        strcat(ip_string_tmp, STRING_CONST_FQHN_AND_IP_SEPARATOR);
                    }
                    strcat(ip_string_tmp, buffer);
                }
            }
            ip_string = strdup(ip_string_tmp);

            freeifaddrs(ifaddr);
        } else if ((status = getaddrinfo(hostname, NULL, &hints, &res)) == 0) { // try alternative approach
            for(p = res; p != NULL; p = p->ai_next) {
                char buffer[MAX_STRING_LEN];
                buffer[0] = '\0';
                void *addr;
                char *ipver;

                // get the pointer to the address itself,
                // different fields in IPv4 and IPv6:
                if (p->ai_family == AF_INET) { // IPv4
                    struct sockaddr_in *ipv4 = (struct sockaddr_in *)p->ai_addr;
                    addr = &(ipv4->sin_addr);
                    ipver = "IPv4";
                } else { // IPv6
                    struct sockaddr_in6 *ipv6 = (struct sockaddr_in6 *)p->ai_addr;
                    addr = &(ipv6->sin6_addr);
                    ipver = "IPv6";
                }

                // Convert the IP to a string and print it:
                inet_ntop(p->ai_family, addr, ipstr, sizeof(ipstr));
                snprintf(buffer, MAX_STRING_LEN-1, "%s%s%s", ipver, STRING_CONST_IPVER_SEPARATOR, ipstr);
                if (strlen(ip_string_tmp) != 0) {
                    strcat(ip_string_tmp, STRING_CONST_FQHN_AND_IP_SEPARATOR);
                }
                strcat(ip_string_tmp, ipstr);
            }
            ip_string = strdup(ip_string_tmp);

            freeaddrinfo(res); // free the linked list
        } else {
            ip_string = strdup(STRING_CONST_IP_ADDRESS_ERROR);
        }
    }

    int fqhn_and_ip_string_len = 0;
    fqhn_and_ip_string_len += strlen(hostname_string);
    fqhn_and_ip_string_len += strlen(STRING_CONST_FQHN_AND_IP_SEPARATOR);
    fqhn_and_ip_string_len += strlen(fqhn_string);
    fqhn_and_ip_string_len += strlen(STRING_CONST_FQHN_AND_IP_SEPARATOR);
    fqhn_and_ip_string_len += strlen(ip_string);
    fqhn_and_ip_string = (char *)malloc((fqhn_and_ip_string_len + 1) * sizeof(char));
    fqhn_and_ip_string[0] = '\0';
    strcat(fqhn_and_ip_string, hostname_string);
    strcat(fqhn_and_ip_string, STRING_CONST_FQHN_AND_IP_SEPARATOR);
    strcat(fqhn_and_ip_string, fqhn_string);
    strcat(fqhn_and_ip_string, STRING_CONST_FQHN_AND_IP_SEPARATOR);
    strcat(fqhn_and_ip_string, ip_string);

    // obtain username and user $HOME
    char *username = NULL;
    char *userhome = NULL;

    uid_t uid = getuid();

    // get the password record for the current user
    struct passwd *pw = getpwuid(uid);
    if (pw == NULL) {
        username = strdup(STRING_CONST_USERNAME_ERROR);
        userhome = strdup(STRING_CONST_USERHOME_ERROR);
    } else {
        username = pw->pw_name;
        userhome = pw->pw_dir;
    }

    // obtain pid, ppid and pgid (process ID, parent process ID and process group ID)
    pid_t pid = getpid();
    pid_t ppid = getppid();
    pid_t pgid = getpgrp();

    char ids_string[MAX_STRING_LEN];
    snprintf(ids_string, MAX_STRING_LEN-1, "%d%s%d%s%d", pid, STRING_CONST_LOG_COLUMN_SEPARATOR, ppid, STRING_CONST_LOG_COLUMN_SEPARATOR, pgid);

    // obtain program name and arguments
    char exe_path[MAX_PATH_LEN];
    snprintf(exe_path, sizeof(exe_path), "/proc/%d/exe", pid);

    char readlink_exe_path[MAX_PATH_LEN];
    char *program_name;
    ssize_t len = readlink(exe_path, readlink_exe_path, sizeof(readlink_exe_path) - 1);
    if (len == -1) {
        program_name = strdup(STRING_CONST_READLINK_ERROR);
    } else {
        // null-terminate the string read by readlink
        readlink_exe_path[len] = '\0';
        program_name = strdup(readlink_exe_path);
    }

    char *program_args_string = NULL;
    char cmdline_path[MAX_PATH_LEN];
    snprintf(cmdline_path, sizeof(cmdline_path), "/proc/%d/cmdline", pid);

    FILE *file = actual_fopen(cmdline_path, "r");
    if (file == NULL) {
        program_args_string = strdup(STRING_CONST_PROGRAM_ARGS_ERROR);
    } else {
        // read file content
        char buffer[MAX_BUFFER_SIZE];
        size_t length = fread(buffer, 1, sizeof(buffer), file);
        fclose(file);
        if (length == 0) {
            program_args_string = strdup(STRING_CONST_PROGRAM_ARGS_ERROR);
        } else {
            program_args_string = (char *)malloc(MAX_BUFFER_SIZE * sizeof(char));
            program_args_string[0] = '\0';
            int pas_len = 0;

            for (size_t i = 0; i < length; ++i) {
                if (buffer[i] == '\0' && i+2 < length) { // only add arg separator if there are more args, +2 to acknowledge last '\0'
                    strcat(program_args_string, STRING_CONST_PROGRAM_ARG_SEPARATOR);
                    pas_len += strlen(STRING_CONST_PROGRAM_ARG_SEPARATOR);
                } else if (buffer[i] == ' ' || buffer[i] == '\t') {
                    strcat(program_args_string, STRING_CONST_PROGRAM_ARG_WHITESPACE_SUBSTITUTE);
                    pas_len += strlen(STRING_CONST_PROGRAM_ARG_WHITESPACE_SUBSTITUTE);
                } else {
                    program_args_string[pas_len++] = buffer[i];
                    program_args_string[pas_len] = '\0';
                }
            }
        }
    }

    // get date+time when program was started
    // AND get elpased time of process (program)
    //   convert start time into micro seconds, obtain the current time in microseconds and calculate the difference
    long long start_time_ticks = get_process_start_time(pid);
    char *program_start_time_string;
    char *elapsed_time_string;
    if (start_time_ticks == -1) {
        program_start_time_string = strdup(STRING_CONST_PROGRAM_START_TIME_ERROR);
        elapsed_time_string = strdup(STRING_CONST_PROGRAM_ELAPSED_TIME_ERROR);
    } else {
        char program_start_time_utc[MAX_STRING_LEN];
        program_start_time_utc[0] = '\0';
        int program_start_time_epoch = -1;
        convert_ticks_to_epoch_and_utc(start_time_ticks, &program_start_time_epoch, program_start_time_utc, sizeof(program_start_time_utc));
        char starttime_tmp[MAX_STRING_LEN];
        starttime_tmp[0] = '\0';
        snprintf(starttime_tmp, MAX_STRING_LEN-1, "%d%s%s", program_start_time_epoch, STRING_CONST_PROGRAM_STARTTIME_SEPARATOR, program_start_time_utc);
        program_start_time_string = strdup(starttime_tmp);

        char elapsed_tmp[MAX_STRING_LEN];
        elapsed_tmp[0] = '\0';
        long ticks_per_second = sysconf(_SC_CLK_TCK);
        long program_start_time_microseconds = (start_time_ticks * 1000000LL) / ticks_per_second;

        struct timespec ts;
        if (clock_gettime(CLOCK_BOOTTIME, &ts) != 0) {
            elapsed_time_string = strdup(STRING_CONST_PROGRAM_ELAPSED_TIME_ERROR);
        } else {
            long time_since_boot_microseconds = ts.tv_sec * 1000000LL + ts.tv_nsec / 1000;
            long program_elapsed_time_microseconds = time_since_boot_microseconds - program_start_time_microseconds;
            snprintf(elapsed_tmp, MAX_STRING_LEN-1, "%ld", program_elapsed_time_microseconds);
            elapsed_time_string = strdup(elapsed_tmp);
        }
    }

    // obtain current working directory
    char cwd[MAX_PATH_LEN];
    char *cwd_string = NULL;

    if (getcwd(cwd, sizeof(cwd)) != NULL) {
        cwd_string = cwd;
    } else {
        cwd_string = strdup(STRING_CONST_GETCWD_ERROR);
    }

    // create log_string
    int log_string_len = 0;
    log_string_len += strlen(time_string);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(fqhn_and_ip_string);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(username);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(userhome);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(ids_string);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(cwd_string);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(program_name);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(program_args_string);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(program_start_time_string);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(elapsed_time_string);
    log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    log_string_len += strlen(func_name);
    if (func_num_args > 0) {
        log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
    }
    for(int i = 0; i < func_num_args; i++) {
        log_string_len += strlen(func_args[i]);
        if (i < func_num_args -1) {
            log_string_len += strlen(STRING_CONST_LOG_COLUMN_SEPARATOR); // add space for column separator
        }
    }
    log_string_len += strlen(STRING_CONST_LOG_NEW_LINE); // add space for new line
    log_string_len++; // add space for null terminator

    char *log_string = (char *)malloc(log_string_len * sizeof(char));
    log_string[0] = '\0';
    strcat(log_string, time_string);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, fqhn_and_ip_string);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, username);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, userhome);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, ids_string);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, cwd_string);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, program_name);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, program_args_string);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, program_start_time_string);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, elapsed_time_string);
    strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    strcat(log_string, func_name);
    if (func_num_args > 0) {
        strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
    }
    for(int i = 0; i < func_num_args; i++) {
        strcat(log_string, func_args[i]);
        if (i < func_num_args -1) {
            strcat(log_string, STRING_CONST_LOG_COLUMN_SEPARATOR); // add column separator
        }
    }
    strcat(log_string, STRING_CONST_LOG_NEW_LINE);

    debug(4, "log_string='%s', strlen(log_string)=%ld\n", log_string, strlen(log_string));

    // use actual_write
    ssize_t bytes_written;
    bytes_written = actual_write(logfd, log_string, strlen(log_string));
    if (bytes_written == -1) {
        perror("Failed to write to file");
    }
    debug(4, "wrote %ld bytes to fd %d\n", bytes_written, logfd);

    // free log_string
    free(log_string);

    // close logfd
    close(logfd);

    return EXIT_SUCCESS;
}

char *map_flags_to_strings(int flags) {
    char *buffer = (char *)malloc(1024 * sizeof(char));
    buffer[0] = '\0';

    if ((flags & O_RDONLY) == O_RDONLY) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_RDONLY");
    }
    if ((flags & O_WRONLY) == O_WRONLY) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_WRONLY");
    }
    if ((flags & O_RDWR) == O_RDWR) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_RDWR");
    }
    if ((flags & O_CREAT) == O_CREAT) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_CREAT");
    }
    if ((flags & O_EXCL) == O_EXCL) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_EXCL");
    }
    if ((flags & O_NOCTTY) == O_NOCTTY) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_NOCTTY");
    }
    if ((flags & O_TRUNC) == O_TRUNC) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_TRUNC");
    }
    if ((flags & O_APPEND) == O_APPEND) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_APPEND");
    }
    if ((flags & O_NONBLOCK) == O_NONBLOCK) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_NONBLOCK");
    }
    if ((flags & O_DSYNC) == O_DSYNC) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_DSYNC");
    }
    if ((flags & O_SYNC) == O_SYNC) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_SYNC");
    }
    if ((flags & O_RSYNC) == O_RSYNC) {
        if (strlen(buffer) > 0) {
            strcat(buffer, "+");
        }
        strcat(buffer, "O_RSYNC");
    }
    
    return buffer;
}

bool starts_with(const char *str, const char *prefix) {
  size_t len_prefix = strlen(prefix);
  size_t len_str = strlen(str);
  return len_str < len_prefix ? false : strncmp(str, prefix, len_prefix) == 0;
}

bool starts_with_any(const char *str, const char *prefixes[], size_t num_prefixes) {
  for (size_t i = 0; i < num_prefixes; i++) {
    if (starts_with(str, prefixes[i])) {
      return true;
    }
  }
  return false;
}

// intercepted calls
FILE *fopen64(const char *pathname, const char *mode) {
    debug(3, "'%s' called for '%s'\n", __func__, pathname);
    char **func_args = create_array_of_strings(2, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%s", mode);
    log_call(__func__, 2, func_args);
    free_array_of_strings(func_args, 2);

    char *local_path;
    // check if pathname begins with "remote" prefixes (https, http, ftp)
    if (starts_with_any(pathname, URL_PREFIXES, NUM_URL_PREFIXES)) {
        // pathname is an URL, download it with curl and open the downloaded file
        // with actual_open; if download fails, set return value to XXX and
        // errno accordingly
        if (download(pathname, &local_path) == 0) {
            debug(3, "download to '%s' successful\n", local_path);
        } else {
            // download failed, set error code and return -1
            errno = ENOENT;
            return NULL;
        }
    } else {
        local_path = strdup(pathname);
    }

    // call the actual fopen64 function
    return actual_fopen64(local_path, mode);
}

FILE *fopen(const char *pathname, const char *mode) {
    debug(3, "'%s' called for '%s'\n", __func__, pathname);
    char **func_args = create_array_of_strings(2, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%s", mode);
    log_call(__func__, 2, func_args);
    free_array_of_strings(func_args, 2);

    char *local_path;
    // check if pathname begins with "remote" prefixes (https, http, ftp)
    if (starts_with_any(pathname, URL_PREFIXES, NUM_URL_PREFIXES)) {
        // pathname is an URL, download it with curl and open the downloaded file
        // with actual_open; if download fails, set return value to XXX and
        // errno accordingly
        if (download(pathname, &local_path) == 0) {
            debug(3, "download to '%s' successful\n", local_path);
        } else {
            // download failed, set error code and return -1
            errno = ENOENT;
            return NULL;
        }
    } else {
        local_path = strdup(pathname);
    }

    // call the actual fopen function
    return actual_fopen(local_path, mode);
}

FILE *freopen(const char *pathname, const char *mode, FILE *stream) {
    debug(3, "'%s' called for '%s'\n", __func__, pathname);
    char **func_args = create_array_of_strings(3, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%s", mode);
    snprintf(func_args[2], MAX_STRING_LEN-1, "%p", stream);
    log_call(__func__, 3, func_args);
    free_array_of_strings(func_args, 3);

    char *local_path;
    // check if pathname begins with "remote" prefixes (https, http, ftp)
    if (starts_with_any(pathname, URL_PREFIXES, NUM_URL_PREFIXES)) {
        // pathname is an URL, download it with curl and open the downloaded file
        // with actual_open; if download fails, set return value to XXX and
        // errno accordingly
        if (download(pathname, &local_path) == 0) {
            debug(3, "download to '%s' successful\n", local_path);
        } else {
            // download failed, set error code and return -1
            errno = ENOENT;
            return NULL;
        }
    } else {
        local_path = strdup(pathname);
    }

    // call the actual fopen function
    return actual_freopen(local_path, mode, stream);
}

FILE *fopenat(int dirfd, const char *pathname, const char *mode) {
    debug(3, "'%s' called for '%s'\n", __func__, pathname);
    int num_func_args = 3;
    char **func_args = create_array_of_strings(num_func_args, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%d", dirfd);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[2], MAX_STRING_LEN-1, "%s", mode);

    log_call(__func__, num_func_args, func_args);
    free_array_of_strings(func_args, num_func_args);

    char *local_path;
    // check if pathname begins with "remote" prefixes (https, http, ftp)
    if (starts_with_any(pathname, URL_PREFIXES, NUM_URL_PREFIXES)) {
        // pathname is an URL, download it with curl and open the downloaded file
        // with actual_open; if download fails, set return value to XXX and
        // errno accordingly
        if (download(pathname, &local_path) == 0) {
            debug(3, "download to '%s' successful\n", local_path);
        } else {
            // download failed, set error code and return -1
            errno = ENOENT;
            return NULL;
        }
    } else {
        local_path = strdup(pathname);
    }

    // call the actual openat function
    return actual_fopenat(dirfd, local_path, mode);
}

int open64(const char *pathname, int flags, mode_t mode) {
    debug(3, "'%s' called for '%s'\n", __func__, pathname);
    char **func_args = create_array_of_strings(3, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%d::%s", flags, map_flags_to_strings(flags));
    snprintf(func_args[2], MAX_STRING_LEN-1, "%d::0%o", mode, mode);
    log_call(__func__, 3, func_args);
    free_array_of_strings(func_args, 3);

    char *local_path;
    // check if pathname begins with "remote" prefixes (https, http, ftp)
    if (starts_with_any(pathname, URL_PREFIXES, NUM_URL_PREFIXES)) {
        // pathname is an URL, download it with curl and open the downloaded file
        // with actual_open; if download fails, set return value to XXX and
        // errno accordingly
        if (download(pathname, &local_path) == 0) {
            debug(3, "download to '%s' successful\n", local_path);
        } else {
            // download failed, set error code and return -1
            errno = ENOENT;
            return -1;
        }
    } else {
        local_path = strdup(pathname);
    }

    return actual_open64(local_path, flags, mode);
}

int openat(int dirfd, const char *pathname, int flags, ...) {
    debug(3, "'%s' called for '%s'\n", __func__, pathname);
    int num_func_args = (flags & O_CREAT ? 4 : 3);
    char **func_args = create_array_of_strings(num_func_args, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%d", dirfd);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[2], MAX_STRING_LEN-1, "%d::%s", flags, map_flags_to_strings(flags));
    
    mode_t mode = 0;

    if (flags & O_CREAT) {
        va_list arg;
        va_start(arg, flags);
        // for use of PROMOTED_MODE_T, see https://github.com/coreutils/gnulib/blob/e7d6a9e033ff82d5bd7f001d6d1a17bd6cc9607c/lib/openat.c#L71-L73
        // mode = va_arg(arg, PROMOTED_MODE_T);
        mode = va_arg(arg, mode_t);
        va_end(arg);
        snprintf(func_args[3], MAX_STRING_LEN-1, "%d::0%o", mode, mode);
    }
    log_call(__func__, num_func_args, func_args);
    free_array_of_strings(func_args, num_func_args);

    char *local_path;
    // check if pathname begins with "remote" prefixes (https, http, ftp)
    if (starts_with_any(pathname, URL_PREFIXES, NUM_URL_PREFIXES)) {
        // pathname is an URL, download it with curl and open the downloaded file
        // with actual_open; if download fails, set return value to XXX and
        // errno accordingly
        if (download(pathname, &local_path) == 0) {
            debug(3, "download to '%s' successful\n", local_path);
        } else {
            // download failed, set error code and return -1
            errno = ENOENT;
            return -1;
        }
    } else {
        local_path = strdup(pathname);
    }

    // call the actual openat function
    if (num_func_args == 4) {
        return actual_openat(dirfd, local_path, flags, mode);
    } else {
        return actual_openat(dirfd, local_path, flags);
    }
}

int open(const char *pathname, int flags, ...) {
    // print debug output to stderr
    debug(3, "'%s' called for '%s'\n", __func__, pathname);

    // log call to log file
    int num_func_args = (flags & O_CREAT ? 3 : 2);
    char **func_args = create_array_of_strings(num_func_args, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%d::%s", flags, map_flags_to_strings(flags));

    mode_t mode = 0;

    if (flags & O_CREAT) {
        va_list arg;
        va_start(arg, flags);
        // for use of PROMOTED_MODE_T, see https://github.com/coreutils/gnulib/blob/e7d6a9e033ff82d5bd7f001d6d1a17bd6cc9607c/lib/openat.c#L71-L73
        // mode = va_arg(arg, PROMOTED_MODE_T);
        mode = va_arg(arg, mode_t);
        va_end(arg);
        snprintf(func_args[2], MAX_STRING_LEN-1, "%d::0%o", mode, mode);
    }
    log_call(__func__, num_func_args, func_args);
    free_array_of_strings(func_args, num_func_args);

    char *local_path;
    // check if pathname begins with "remote" prefixes (https, http, ftp)
    if (starts_with_any(pathname, URL_PREFIXES, NUM_URL_PREFIXES)) {
        // pathname is an URL, download it with curl and open the downloaded file
        // with actual_open; if download fails, set return value to XXX and
        // errno accordingly
        if (download(pathname, &local_path) == 0) {
            debug(3, "download to '%s' successful\n", local_path);
        } else {
            // download failed, set error code and return -1
            errno = ENOENT;
            return -1;
        }
    } else {
        local_path = strdup(pathname);
    }

    if (num_func_args == 3) {
      return actual_open(local_path, flags, mode);
    } else {
      return actual_open(local_path, flags);
    }
}
