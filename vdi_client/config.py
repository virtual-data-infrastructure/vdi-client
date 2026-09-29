# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - configuration file handling.

Loads optional shell-style configuration files that may define ``BASE_URL``
and other environment variables used by the VDI client.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".vdi" / "config"


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
