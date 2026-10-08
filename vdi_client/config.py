# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - configuration file handling.

Loads optional shell-style configuration files that may define ``BASE_URL``
and other environment variables used by the VDI client.

This module also defines constants and resolution helpers for log file
location and naming (used by the ``log`` subcommand).
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".vdi" / "config"

# --- Log file configuration ---

# Environment variables that configure log file location and naming.
VDI_LOG_DIR_ENV = "VDI_LOG_DIR"
VDI_LOG_PREFIX_ENV = "VDI_LOG_FILE_PREFIX"

# Defaults matching the wrapper library behaviour.
DEFAULT_LOG_DIR = Path.home() / ".vdi" / "logs"
DEFAULT_LOG_PREFIX = "vdi_log."


def resolve_log_dir(log_dir_override: str | None = None) -> Path:
    """Resolve the directory where VDI log files are stored.

    The lookup order is:

    1. Explicit ``log_dir_override`` (from ``--log-dir`` flag).
    2. ``VDI_LOG_DIR`` environment variable.
    3. ``${HOME}/.vdi/logs/`` (default).

    Args:
        log_dir_override: Optional explicit path passed on the command line.

    Returns:
        The resolved :class:`~pathlib.Path` to the log directory.
    """
    if log_dir_override:
        return Path(log_dir_override)
    env_dir = os.environ.get(VDI_LOG_DIR_ENV)
    if env_dir:
        return Path(env_dir)
    return DEFAULT_LOG_DIR


def resolve_log_prefix(log_prefix_override: str | None = None) -> str:
    """Resolve the prefix used for VDI log file names.

    The lookup order is:

    1. Explicit ``log_prefix_override`` (from ``--log-prefix`` flag).
    2. ``VDI_LOG_FILE_PREFIX`` environment variable.
    3. ``vdi_log.`` (default).

    Args:
        log_prefix_override: Optional explicit prefix passed on the command line.

    Returns:
        The resolved prefix string.
    """
    if log_prefix_override is not None:
        return log_prefix_override
    return os.environ.get(VDI_LOG_PREFIX_ENV, DEFAULT_LOG_PREFIX)


def load_config(config_path: Path | None = None) -> dict[str, str]:
    """Load a VDI configuration file into a dictionary.

    The config file is sourced shell-style: each line should be a
    ``KEY=VALUE`` assignment. Lines starting with ``#`` are ignored.

    Args:
        config_path: Path to the config file. If ``None``, the default
            path (``${HOME}/.vdi/config``) is used.

    Returns:
        A dictionary of configuration key-value pairs. Returns an empty
        dict if the file does not exist.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config: dict[str, str] = {}

    if not config_path.is_file():
        return config

    with config_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes if present
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            config[key] = value

    return config


def resolve_base_url(
    cli_base_url: str | None,
    config: dict[str, str],
) -> str | None:
    """Resolve the VDI server base URL from CLI args or config.

    Args:
        cli_base_url: Base URL provided via ``--base-url`` on the command line.
        config: Configuration dictionary loaded from the config file.

    Returns:
        The resolved base URL, or ``None`` if not set.
    """
    if cli_base_url:
        return cli_base_url
    return config.get("BASE_URL") or os.environ.get("BASE_URL")
