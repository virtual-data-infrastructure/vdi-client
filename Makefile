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
EESSI_PYTHON = $(EESSI_EPREFIX)/bin/python

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
# 3. build the wheel with the EESSI compat-layer Python
build-wheel: install-library $(PKG_LIB_DIR)/$(TARGET)
	$(EESSI_PYTHON) -m build --wheel

$(PKG_LIB_DIR)/$(TARGET): $(LIB_DIR)/$(TARGET)
	mkdir -p $(PKG_LIB_DIR)
	cp $< $@

# clean the build artifacts in the subdirectory and remove the installed files
clean:
	$(MAKE) -C $(VDI_SRCS_DIR) clean

clean-install:
	$(MAKE) -C $(VDI_SRCS_DIR) clean-install
	rm $(BIN_DIR)/$(SCRIPT)

clean-wheel:
	rm -rf $(PKG_LIB_DIR)
	rm -rf dist

clean-all: clean clean-install

# phony targets
.PHONY: all install install-script install-library build-wheel clean clean-install clean-wheel clean-all
