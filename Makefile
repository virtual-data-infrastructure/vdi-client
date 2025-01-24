# directories
BIN_DIR = bin
LIB_DIR = lib64
VDI_SRCS_DIR = src/vdi_wrapper

# files
SCRIPT = vdi
TARGET = libvdi.so

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

# clean the buld artifacts in the subdirectory and remove the installed files
clean:
	$(MAKE) -C $(VDI_SRCS_DIR) clean

clean-install:
	$(MAKE) -C $(VDI_SRCS_DIR) clean-install
	rm $(BIN_DIR)/$(SCRIPT)

clean-all: clean clean-install

# phony targets
.PHONY: all install install-script install-library clean clean-install clean-all
