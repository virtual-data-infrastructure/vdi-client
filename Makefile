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

# build a wheel that bundles the pre-built shared library
# 1. compile libvdi.so via the subdirectory Makefile (requires EESSI)
# 2. copy it into the package tree (vdi_client/lib/)
# 3. build the wheel using the 'build' package; if it is not available,
#    a temporary venv is created, pip is upgraded, and 'build' is installed
#
# To use a persistent venv instead (e.g. for debugging or repeated builds),
# create one manually:
#
#     $(EESSI_PYTHON) -m venv $(BUILD_VENV)
#     source $(BUILD_VENV)/bin/activate
#     pip install --upgrade pip
#     pip install build
#     make build-wheel
#     deactivate
#
# The persistent venv will be detected and reused; remove it with
# 'rm -rf $(BUILD_VENV)' or 'make clean-wheel'.
build-wheel: install-library $(PKG_LIB_DIR)/$(TARGET)
	@if [ -x "$(BUILD_VENV)/bin/python" ]; then \
		echo "Using existing virtual environment at $(BUILD_VENV) ..."; \
		$(BUILD_VENV)/bin/python -m build --wheel; \
	elif $(EESSI_PYTHON) -c "import build.__main__" 2>/dev/null; then \
		$(EESSI_PYTHON) -m build --wheel; \
	else \
		echo "No 'build' module found; creating temporary virtual environment at $(BUILD_VENV) ..."; \
		$(EESSI_PYTHON) -m venv $(BUILD_VENV); \
		$(BUILD_VENV)/bin/python -m pip install --quiet --upgrade pip; \
		$(BUILD_VENV)/bin/python -m pip install --quiet build; \
		$(BUILD_VENV)/bin/python -m build --wheel; \
		rm -rf $(BUILD_VENV); \
		echo "To use a persistent venv, see the comment above the build-wheel target in the Makefile."; \
	fi

$(PKG_LIB_DIR)/$(TARGET): $(LIB_DIR)/$(TARGET)
	mkdir -p $(PKG_LIB_DIR)
	cp $< $@

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
.PHONY: all install install-script install-library build-wheel clean clean-install clean-wheel clean-all
