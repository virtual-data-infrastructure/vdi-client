# directories
BIN_DIR = bin
LIB_DIR = lib64
VDI_SRCS_DIR = src/vdi_wrapper

# files
SCRIPT = vdi
TARGET = libvdi.so

# package directory for the bundled shared library (used by build-wheel)
PKG_LIB_DIR = vdi_client/lib

# Python interpreter from the EESSI compat layer (used for building wheels)
EESSI_PYTHON = $(EESSI_EPREFIX)/usr/bin/python

# temporary virtual environment for wheel building
BUILD_VENV = .build-venv

# EESSI stack version (e.g. "2023.06"); when set, the built library is
# installed as libvdi_eessi{EESSI_VERSION}.so so that multiple EESSI versions
# can coexist and be bundled into a single fat wheel per architecture.
EESSI_VERSION ?=

# default target to install both the script and the shared library
all: install

# install target
install: install-library install-script

# install the script into the BIN_DIR directory
install-script: $(BIN_DIR)/$(SCRIPT)
	@echo "Installed script '$(SCRIPT)' into directory '$(BIN_DIR)'. Run it with '$(BIN_DIR)/$(SCRIPT)' or add directory '$(BIN_DIR)' to PATH and simply run '$(SCRIPT)'"

$(BIN_DIR)/$(SCRIPT): $(SCRIPT)
	mkdir -p $(BIN_DIR)
	cp $< $(BIN_DIR)/

# call the subdirectory Makefile to compile, link, and install the shared library
install-library:
	$(MAKE) -C $(VDI_SRCS_DIR) install

# compile and install the shared library with an EESSI-versioned filename
# (e.g. libvdi_eessi2023.06.so). Requires EESSI to be initialized and
# EESSI_VERSION to be set. The subdirectory Makefile builds libvdi.so
#
# The wrapper build directory is cleaned first to force a fresh compile
# with the correct RUNPATH for the active EESSI version (otherwise Make
# would skip recompilation since vdi.c hasn't changed between versions).
install-library-versioned: clean install-library
ifndef EESSI_VERSION
	$(error EESSI_VERSION is not set; run 'make install-library-versioned EESSI_VERSION=2023.06')
endif
	@if [ -f "$(LIB_DIR)/$(TARGET)" ]; then \
		mv "$(LIB_DIR)/$(TARGET)" "$(LIB_DIR)/libvdi_eessi$(EESSI_VERSION).so"; \
		echo "Installed versioned library: $(LIB_DIR)/libvdi_eessi$(EESSI_VERSION).so"; \
	else \
		echo "Error: $(LIB_DIR)/$(TARGET) not found after build"; exit 1; \
	fi

# build a fat wheel that bundles all pre-built versioned shared libraries
# (libvdi_eessi*.so). This target does NOT require EESSI - it only needs
# Python and the 'build' package. The versioned .so files must already
# exist in $(LIB_DIR)/ (built via 'make install-library-versioned' for
# each EESSI version).
#
# To use a persistent venv instead (e.g. for debugging or repeated builds),
# create one manually:
#
#     python -m venv $(BUILD_VENV)
#     source $(BUILD_VENV)/bin/activate
#     pip install --upgrade pip
#     pip install build
#     make build-wheel
#     deactivate
#
# The persistent venv will be detected and reused; remove it with
# 'rm -rf $(BUILD_VENV)' or 'make clean-wheel'.
build-wheel: copy-versioned-libs
	@UNAME_M=$$(uname -m); \
	if [ "$$UNAME_M" = "x86_64" ]; then PLAT_NAME=manylinux2014_x86_64; \
	elif [ "$$UNAME_M" = "aarch64" ] || [ "$$UNAME_M" = "arm64" ]; then PLAT_NAME=manylinux2014_aarch64; \
	elif [ "$$UNAME_M" = "riscv64" ]; then PLAT_NAME=manylinux2014_riscv64; \
	else echo "Unsupported architecture: $$UNAME_M"; exit 1; fi; \
	echo "Building wheel for platform: $$PLAT_NAME"; \
	if [ -x "$(BUILD_VENV)/bin/python" ]; then \
		echo "Using existing virtual environment at $(BUILD_VENV) ..."; \
		$(BUILD_VENV)/bin/python -m build --wheel -C--build-option=--plat-name=$$PLAT_NAME; \
	elif command -v python >/dev/null 2>&1 && python -c "import build.__main__" 2>/dev/null; then \
		python -m build --wheel -C--build-option=--plat-name=$$PLAT_NAME; \
	else \
		echo "No 'build' module found; creating temporary virtual environment at $(BUILD_VENV) ..."; \
		python -m venv $(BUILD_VENV); \
		$(BUILD_VENV)/bin/python -m pip install --quiet --upgrade pip; \
		$(BUILD_VENV)/bin/python -m pip install --quiet build; \
		$(BUILD_VENV)/bin/python -m build --wheel -C--build-option=--plat-name=$$PLAT_NAME; \
		rm -rf $(BUILD_VENV); \
		echo "To use a persistent venv, see the comment above the build-wheel target in the Makefile."; \
	fi

copy-versioned-libs:
	@mkdir -p $(PKG_LIB_DIR)
	@libs_found=0; \
	for lib in $(LIB_DIR)/libvdi_eessi*.so; do \
		if [ -f "$$lib" ]; then \
			cp "$$lib" $(PKG_LIB_DIR)/; \
			echo "Bundled: $$(basename $$lib)"; \
			libs_found=$$((libs_found + 1)); \
		fi; \
	done; \
	if [ "$$libs_found" -eq 0 ]; then \
		echo "Error: no versioned libraries found in $(LIB_DIR)/ (expected libvdi_eessi*.so)"; \
		echo "Build them with 'make install-library-versioned EESSI_VERSION=<version>' for each EESSI version."; \
		exit 1; \
	fi

# clean the build artifacts in the subdirectory and remove the installed files
clean:
	$(MAKE) -C $(VDI_SRCS_DIR) clean

clean-install:
	$(MAKE) -C $(VDI_SRCS_DIR) clean-install
	rm -f $(BIN_DIR)/$(SCRIPT)

clean-wheel:
	rm -rf $(PKG_LIB_DIR)
	rm -rf build
	rm -rf dist
	rm -rf $(BUILD_VENV)

clean-all: clean clean-install clean-wheel

# phony targets
.PHONY: all install install-script install-library install-library-versioned build-wheel copy-versioned-libs clean clean-install clean-wheel clean-all
