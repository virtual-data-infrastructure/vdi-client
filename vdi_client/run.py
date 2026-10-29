# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - ``run`` subcommand.

Runs a user program with the VDI shared library (``libvdi.so``) loaded
via ``LD_PRELOAD`` so that file-system calls are intercepted and logged.
"""

from __future__ import annotations

import ctypes
import os
import re
import sys
from pathlib import Path

# Environment variable that may override the default library path.
VDI_LIB_PATH_ENV = "VDI_LIB_PATH"

# Pattern to extract the EESSI version from an EESSI_EPREFIX path such as
# /cvmfs/software.eessi.io/versions/2023.06/compat/linux/x86_64
_EESSI_VERSION_RE = re.compile(r"/versions/(\d{4}\.\d{2})/")
_EESSI_VERSION_FORMAT_RE = re.compile(r"^\d{4}\.\d{2}$")


def detect_eessi_version() -> str | None:
    """Detect the active EESSI version.

    ``EESSI_VERSION`` is preferred when set; otherwise the version is parsed
    from ``EESSI_EPREFIX``.

    Returns:
        The EESSI version string (e.g. ``"2023.06"``) or ``None`` if the
        environment variable is not set or the version cannot be parsed.
    """
    version = os.environ.get("EESSI_VERSION")
    if version and _EESSI_VERSION_FORMAT_RE.fullmatch(version):
        return version

    eprefix = os.environ.get("EESSI_EPREFIX")
    if not eprefix:
        return None
    match = _EESSI_VERSION_RE.search(eprefix)
    return match.group(1) if match else None


def read_embedded_eessi_version(lib_path: Path) -> str | None:
    """Read the EESSI version embedded in a VDI shared library.

    Args:
        lib_path: Path to the shared library.

    Returns:
        The embedded version, or ``None`` if it is unavailable or malformed.
    """
    try:
        library = ctypes.CDLL(str(lib_path))
        version_function = library.vdi_eessi_version
    except (OSError, AttributeError):
        return None

    version_function.restype = ctypes.c_char_p
    version = version_function()
    if version is None:
        return None

    try:
        decoded = version.decode("ascii")
    except UnicodeDecodeError:
        return None
    return decoded if _EESSI_VERSION_FORMAT_RE.fullmatch(decoded) else None


def resolve_lib_path(lib_override: str | None = None) -> Path:
    """Resolve the path to the VDI shared library.

    The lookup order is:

    1. Explicit ``lib_override`` (from ``--lib`` flag).
    2. ``VDI_LIB_PATH`` environment variable.
    3. ``<package_dir>/lib/libvdi_eessi{version}.so`` - the versioned
       library matching the active EESSI version (detected from
       ``EESSI_EPREFIX``), bundled in a fat wheel.
    4. ``<package_dir>/lib/libvdi.so`` - unversioned fallback (dev layout
       or single-version wheel).
    5. ``<package_dir>/../lib64/libvdi.so`` - development layout, matches
       the bash script.

    Args:
        lib_override: Optional explicit path passed on the command line.

    Returns:
        The resolved :class:`~pathlib.Path` to the shared library.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
    """
    if lib_override:
        candidate = Path(lib_override)
    else:
        env_path = os.environ.get(VDI_LIB_PATH_ENV)
        if env_path:
            candidate = Path(env_path)
        else:
            package_dir = Path(__file__).resolve().parent
            lib_dir = package_dir / "lib"

            # Try versioned library matching the active EESSI version
            eessi_version = detect_eessi_version()
            if eessi_version:
                versioned_candidate = lib_dir / f"libvdi_eessi{eessi_version}.so"
                if versioned_candidate.is_file():
                    candidate = versioned_candidate
                    candidate = candidate.resolve()
                    if not candidate.is_file():
                        raise FileNotFoundError(
                            f"VDI shared library not found at '{candidate}'. "
                            f"Set the {VDI_LIB_PATH_ENV} environment variable or use --lib to specify its location."
                        )
                    return candidate

            # Fall back to unversioned library in wheel layout
            wheel_candidate = lib_dir / "libvdi.so"
            if wheel_candidate.is_file():
                candidate = wheel_candidate
            else:
                # Development layout
                candidate = package_dir / ".." / "lib64" / "libvdi.so"

    candidate = candidate.resolve()
    if not candidate.is_file():
        raise FileNotFoundError(
            f"VDI shared library not found at '{candidate}'. "
            f"Set the {VDI_LIB_PATH_ENV} environment variable or use --lib to specify its location."
        )
    return candidate


def _validate_library_version(lib_path: Path) -> None:
    """Validate that a selected library matches the active EESSI version.

    Args:
        lib_path: Path to the selected VDI shared library.

    Raises:
        RuntimeError: If no active EESSI version is detectable, the library has
            no readable embedded version, or the two versions differ.
    """
    active_version = detect_eessi_version()
    if active_version is None:
        raise RuntimeError("Could not detect the active EESSI version.")

    embedded_version = read_embedded_eessi_version(lib_path)
    if embedded_version is None:
        raise RuntimeError(f"Could not determine the EESSI version embedded in '{lib_path}'.")

    if active_version != embedded_version:
        raise RuntimeError(
            f"VDI library '{lib_path}' was built for EESSI {embedded_version}, "
            f"but the active EESSI version is {active_version}."
        )


def run(
    program: str | None,
    program_args: list[str],
    *,
    lib_override: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Run a user program with ``LD_PRELOAD`` set to the VDI library.

    Args:
        program: Path to the program to execute. If ``None``, an error is
            printed and a non-zero exit code is returned.
        program_args: Additional arguments passed to the program.
        lib_override: Optional explicit path to ``libvdi.so``.
        dry_run: If ``True``, print what would be executed without running it.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error). When the program is
        actually executed, this function does not return - the process is
        replaced via :func:`os.execvpe`.
    """
    if program is None:
        print("Error: no program specified.", file=sys.stderr)
        return 1

    try:
        lib_path = resolve_lib_path(lib_override)
        _validate_library_version(lib_path)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    full_args = [program, *program_args]

    if dry_run:
        print(f"dry-run: run '{' '.join(full_args)}'")
        if verbose:
            print(f"  LD_PRELOAD={lib_path}")
        return 0

    if verbose:
        print(f"run 'LD_PRELOAD={lib_path} {' '.join(full_args)}'")

    env = dict(os.environ)
    env["LD_PRELOAD"] = str(lib_path)

    # Replace the current process with the user program.
    # If execvpe fails (e.g. file not found), report and return an error code.
    try:
        os.execvpe(program, full_args, env)
    except OSError as exc:
        print(f"Error: failed to execute '{program}': {exc}", file=sys.stderr)
        return 1

    # Unreachable in normal operation, but satisfies type checkers.
    return 1  # pragma: no cover
