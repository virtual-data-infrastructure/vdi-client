# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
Custom local version scheme for setuptools_scm.

When the environment variable ``VDI_EESSI_VERSION`` is set (e.g.
``2023.06``), the local version segment ``eessi2023.06`` is appended to
the project version, producing wheel filenames such as
``vdi_client-0.1.0+eessi2023.06-...whl``.

This allows publishing multiple wheels per release - one for each
``{architecture, EESSI_version}`` combination - without filename
collisions on PyPI.
"""

from __future__ import annotations

import os


def local_scheme(version: object) -> str:
    """Return a local version segment encoding the EESSI version.

    Args:
        version: The version object provided by setuptools_scm.

    Returns:
        A local version segment string (e.g. ``eessi2023.06``), or an
        empty string when ``VDI_EESSI_VERSION`` is not set.
    """
    eessi_version = os.environ.get("VDI_EESSI_VERSION")
    if eessi_version:
        return f"eessi{eessi_version}"
    return ""
