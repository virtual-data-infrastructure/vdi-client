# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - client tools for the virtual data infrastructure.

This module provides initialization logic for the package.
"""

try:
    from importlib.metadata import version

    __version__ = version("vdi-client")
except Exception:  # pragma: no cover
    __version__ = "unknown"
