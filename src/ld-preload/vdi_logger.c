#include <ctype.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

bool _global_show_log_path = true;

const int MAX_BUFFER_SIZE = 1024;
const int MAX_PATH_LEN = 1024;
const int MAX_STRING_LEN = 1024;

const char* STRING_CONST_OPEN_FUNCNAME = "open";
const char* STRING_CONST_WRITE_FUNCNAME = "write";
const char* STRING_CONST_LOG_COLUMN_SEPARATOR = " ";
const char* STRING_CONST_LOG_NEW_LINE = "\n";
const char* STRING_CONST_ENVVAR_VDI_LOG_DIR = "VDI_LOG_DIR";
const char* STRING_CONST_ENVVAR_DEFAULT_VDI_LOG_DIR = "${HOME}/.vdi/logs";
const char* STRING_CONST_ENVVAR_VDI_LOG_FILE_PREFIX = "VDI_LOG_FILE_PREFIX";
const char* STRING_CONST_ENVVAR_DEFAULT_VDI_LOG_FILE_PREFIX = "vdi_log.";

int (*actual_open)() = NULL;
int (*actual_write)() = NULL;

// helper functions
char** create_array_of_strings(int num_strings, int string_len) {
    char **array = (char **)malloc(num_strings * sizeof(char*));
    for(int i = 0; i < num_strings; i++) {
        array[i] = (char *)malloc(string_len * sizeof(char));
        array[i][0] = '\0';
    }
    return array;
}

int create_dir(const char *pathname) {
    struct stat st;

    // check if the directory exists
    if (stat(pathname, &st) == 0) {
        if (S_ISDIR(st.st_mode)) {
            // pathname already exists and is a directory
            return EXIT_SUCCESS;
        } else {
            // pathname exists but is not a directory
            return EXIT_FAILURE;
        }
    } else {
        // pathname does not exist yet
        if (errno == ENOENT) {
            if (mkdir(pathname, 0755) == 0) {
                return EXIT_SUCCESS;
            } else {
                return EXIT_FAILURE;
            }
        } else {
            return EXIT_FAILURE;
        }
    }
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

    snprintf(log_path, MAX_PATH_LEN, "%s/%s%d", env_vdi_log_dir, env_vdi_log_file_prefix, pid);
    return log_path;
}

int log_call(const char *func_name, int func_num_args, char **func_args) {
    if (actual_open == NULL) {
        actual_open = dlsym(RTLD_NEXT, STRING_CONST_OPEN_FUNCNAME);
    }
    char *log_path = get_log_path();
    if (_global_show_log_path) {
        printf("vdi_logger.so: using log file '%s'\n", log_path);
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

    // create log_string
    int log_string_len = 0;
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

    // printf("vdi_logger: log_string='%s', strlen(log_string)=%ld\n", log_string, strlen(log_string));

    if (actual_write == NULL) {
        actual_write = dlsym(RTLD_NEXT, STRING_CONST_WRITE_FUNCNAME);
    }
    // use actual_write
    ssize_t bytes_written;
    bytes_written = actual_write(logfd, log_string, strlen(log_string));
    if (bytes_written == -1) {
        perror("Failed to write to file");
    }
    // printf("wrote %ld bytes to fd %d\n", bytes_written, logfd);

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

// intercepted calls
FILE *fopen(const char *pathname, const char *mode) {
    char **func_args = create_array_of_strings(2, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%s", mode);
    log_call(__func__, 2, func_args);
    free_array_of_strings(func_args, 2);

    // call the actual open64 function
    FILE* (*actual_fopen)() = dlsym(RTLD_NEXT, __func__);
    return actual_fopen(pathname, mode);
}

//bfd *bfd_openr(const char *filename, const char *target) {
//    char **func_args = create_array_of_strings(2, MAX_STRING_LEN);
//    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", filename);
//    snprintf(func_args[1], MAX_STRING_LEN-1, "%s", target);
//    log_call(__func__, 2, func_args);
//    free_array_of_strings(func_args, 2);
//
//    // call the actual bfd_openr function
//    bfd* (*actual_bfd_openr)() = dlsym(RTLD_NEXT, __func__);
//    return actual_bfd_openr(filename, target);
//}

int open64(const char *pathname, int flags, mode_t mode) {
    char **func_args = create_array_of_strings(3, MAX_STRING_LEN);
    snprintf(func_args[0], MAX_STRING_LEN-1, "%s", pathname);
    snprintf(func_args[1], MAX_STRING_LEN-1, "%d::%s", flags, map_flags_to_strings(flags));
    snprintf(func_args[2], MAX_STRING_LEN-1, "%d::0%o", mode, mode);
    log_call(__func__, 3, func_args);
    free_array_of_strings(func_args, 3);

    // call the actual open64 function
    int (*actual_open64)() = dlsym(RTLD_NEXT, __func__);
    return actual_open64(pathname, flags, mode);
}

int openat(int dirfd, const char *pathname, int flags, ...) {
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

    // call the actual openat function
    int (*actual_openat)() = dlsym(RTLD_NEXT, __func__);
    if (num_func_args == 4) {
        return actual_openat(dirfd, pathname, flags, mode);
    } else {
        return actual_openat(dirfd, pathname, flags);
    }
}

int open(const char *pathname, int flags, ...) {
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

    // call the actual open function
    int (*actual_open)() = dlsym(RTLD_NEXT, __func__);
    if (num_func_args == 3) {
        return actual_open(pathname, flags, mode);
    } else {
        return actual_open(pathname, flags);
    }
}
