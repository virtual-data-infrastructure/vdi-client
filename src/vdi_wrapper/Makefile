# determine CPU family
ARCH := $(shell uname -m)

# define the compiler and flags
CC = gcc
CFLAGS = -fPIC -shared -Wall -Wextra -Werror -g
LDFLAGS = -ldl

# determine path to compiler set by CC
PATH_TO_CC := $(shell command -v ${CC})

# specify directories for building and installing
BUILD_DIR = build
INSTALL_DIR = ../../lib64

# target shared library
TARGET = libvdi.so

# source files
SRCS = vdi.c

# object file (in the build directory)
OBJ = $(BUILD_DIR)/$(TARGET)

# default target
all: is_eessi_initialized compiler_from_compat_layer $(BUILD_DIR) $(OBJ)

# function to check if EESSI is initialized
is_eessi_initialized:
ifndef EESSI_EPREFIX
	$(error EESSI_EPREFIX is not set; ensure that EESSI is initialized before running make)
endif

# function to check if compiler from compatibility layer (prefix ${EESSI_EPREFIX}) is used
define COMPILER_FROM_COMPAT_LAYER_MSG
The wrong compiler $(PATH_TO_CC) would be used,
due to the value of the PATH environment variable. Possibly, a module from the software layer is loaded.

Please, check output of 'module list', unload compiler modules such as GCC or GCCcore, and rerun make.
endef

compiler_from_compat_layer:
ifneq ($(findstring ${EESSI_EPREFIX},$(PATH_TO_CC)),${EESSI_EPREFIX})
	$(error $(COMPILER_FROM_COMPAT_LAYER_MSG))
endif

# ensure the build directory exists
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# build the shared library in the build directory
$(OBJ): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# install the shared library to the installation directory
install: all
	mkdir -p $(INSTALL_DIR)
	cp $(OBJ) $(INSTALL_DIR)/

# clean rule (remove build artifacts)
clean:
	rm -rf $(BUILD_DIR)

# clean install (removes installed files)
clean-install:
	rm -f $(INSTALL_DIR)/$(TARGET)

# clean all (removes build artifacts and installed files)
clean-all: clean clean-install

# phony targets
.PHONY: all clean install $(BUILD_DIR) clean-install clean-all is_eessi_initialized compiler_from_compat_layer
