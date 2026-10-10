# determine CPU family
ARCH := $(shell uname -m)

# define the compiler and flags
CC = gcc
CFLAGS = -fPIC -shared -Wall -Wextra -Werror -g
# embed RUNPATH so libvdi.so finds its EESSI dependencies (libcurl, libdl)
# without relying on LD_LIBRARY_PATH (which must not be used with EESSI)
LDFLAGS = -ldl -lcurl -lpthread -Wl,-rpath,$(EESSI_EPREFIX)/lib -Wl,--enable-new-dtags

# expected RUNPATH value embedded in the shared library
EXPECTED_RUNPATH = $(EESSI_EPREFIX)/lib

# tool to inspect ELF dynamic section
READELF = readelf

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

# compile target
compile: is_eessi_initialized compiler_from_compat_layer clean_environment $(BUILD_DIR) $(OBJ)

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

# function to check that the environment is clean for building against EESSI
# LD_LIBRARY_PATH must not be set (EESSI uses RPATH/RUNPATH, not LD_LIBRARY_PATH)
# LIBRARY_PATH may only contain paths under ${EESSI_EPREFIX}
define LD_LIBRARY_PATH_SET_MSG
LD_LIBRARY_PATH is set to '$(LD_LIBRARY_PATH)'.
EESSI does not use LD_LIBRARY_PATH; setting it may cause library conflicts.
Please unset LD_LIBRARY_PATH and rerun make.
endef

define LIBRARY_PATH_NOT_CLEAN_MSG
LIBRARY_PATH contains paths outside of the EESSI compat layer:
  LIBRARY_PATH='$(LIBRARY_PATH)'
Only paths under '${EESSI_EPREFIX}' are allowed.
Please clean LIBRARY_PATH and rerun make.
endef

clean_environment:
ifdef LD_LIBRARY_PATH
	$(error $(LD_LIBRARY_PATH_SET_MSG))
endif
ifneq ($(LIBRARY_PATH),)
$(foreach p,$(filter-out $(EESSI_EPREFIX)%,$(subst :, ,$(LIBRARY_PATH))),$(error $(LIBRARY_PATH_NOT_CLEAN_MSG)))
endif

# ensure the build directory exists
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# build the shared library in the build directory
$(OBJ): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# verify that the built shared library has the expected RUNPATH entry
# uses readelf -d to inspect the ELF dynamic section and checks for a
# RUNPATH (DT_RUNPATH) entry matching $(EXPECTED_RUNPATH)
verify_rpath: $(OBJ)
	@if ! $(READELF) -d $(OBJ) | grep -q 'RUNPATH.*$(EXPECTED_RUNPATH)'; then \
		echo "Error: $(OBJ) does not contain a RUNPATH entry matching $(EXPECTED_RUNPATH)."; \
		echo "Run 'readelf -d $(OBJ)' to inspect the dynamic section."; \
		exit 1; \
	fi
	@echo "Verified: RUNPATH contains '$(EXPECTED_RUNPATH)' in $(OBJ)"

# install the shared library to the installation directory
install: compile verify_rpath
	mkdir -p $(INSTALL_DIR)
	cp $(OBJ) $(INSTALL_DIR)/

# default target
all: install

# clean rule (remove build artifacts)
clean:
	rm -rf $(BUILD_DIR)

# clean install (removes installed files)
clean-install:
	rm -f $(INSTALL_DIR)/$(TARGET)

# clean all (removes build artifacts and installed files)
clean-all: clean clean-install

# phony targets
.PHONY: all build clean install $(BUILD_DIR) clean-install clean-all \
        is_eessi_initialized compiler_from_compat_layer clean_environment \
        verify_rpath
