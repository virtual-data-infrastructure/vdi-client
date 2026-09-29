# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""
VDI client - ``view`` subcommand.

Provides subcommands to create, list, delete, inspect, upload to and
remove files from *views* on a VDI server via its REST API.

All HTTP requests use the standard-library :mod:`urllib.request` module
so that no third-party dependencies are required.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

# Type alias for a parsed JSON object (dictionary).
JSONDict = dict[str, Any]
# Type alias for a parsed JSON array of objects.
JSONList = list[JSONDict]


class VDIError(Exception):
    """Raised when a VDI server request fails."""


def _parse_json(body: str) -> JSONDict | JSONList:
    """Parse a JSON string into a typed dict or list, raising :class:`VDIError` on failure."""
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise VDIError(f"Failed to parse response: {exc}") from exc

    if isinstance(result, dict):
        return cast(JSONDict, result)
    if isinstance(result, list):
        return cast(JSONList, result)
    raise VDIError(f"Unexpected JSON type: {type(result).__name__}")


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> JSONDict | JSONList:
    """Perform an HTTP request against the VDI server and parse JSON.

    Args:
        base_url: Base URL of the VDI server (no trailing slash).
        method: HTTP method (``GET``, ``POST``, ``DELETE``, ...).
        path: Path appended to ``base_url`` (must start with ``/``).
        data: Optional request body as raw bytes.
        headers: Optional extra HTTP headers.

    Returns:
        Parsed JSON response as a ``dict`` or ``list``.

    Raises:
        VDIError: If the request fails or the response is not valid JSON.
    """
    url = f"{base_url.rstrip('/')}{path}"
    all_headers: dict[str, str] = {}
    if headers:
        all_headers.update(headers)

    req = urllib.request.Request(url, data=data, method=method, headers=all_headers)

    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        if body:
            try:
                parsed = _parse_json(body)
            except VDIError:
                msg = body
            else:
                msg = str(parsed.get("message", body)) if isinstance(parsed, dict) else body
        else:
            msg = ""
        raise VDIError(f"HTTP {exc.code}: {msg}") from exc
    except urllib.error.URLError as exc:
        raise VDIError(f"Failed to connect to backend server: {exc}") from exc

    if not body:
        return {}

    return _parse_json(body)


def _get_views(base_url: str) -> JSONList:
    """Fetch the list of all views from the server."""
    result = _request(base_url, "GET", "/views")
    if isinstance(result, list):
        return result
    return []


def _get_view_id_by_name(base_url: str, name: str) -> str | None:
    """Look up a view's ID by its name.

    Returns:
        The view ID as a string, or ``None`` if no view with that name exists.
    """
    for view in _get_views(base_url):
        if view.get("name") == name:
            view_id = view.get("id")
            if view_id is not None:
                return str(view_id)
    return None


def _extract_message(response: JSONDict | JSONList) -> str:
    """Extract a ``message`` field from a JSON response dict."""
    if isinstance(response, dict):
        return str(response.get("message", ""))
    return ""


def create_view(base_url: str, view_name: str, *, dry_run: bool = False, verbose: bool = False) -> int:
    """Create a new view on the VDI server.

    Args:
        base_url: Base URL of the VDI server.
        view_name: Name of the view to create.
        dry_run: If ``True``, print what would be done without contacting the server.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    if dry_run:
        print(f"dry-run: create view '{view_name}'")
        return 0

    if verbose:
        print(f"Creating view '{view_name}' at {base_url}/views")

    data = json.dumps({"name": view_name}).encode("utf-8")
    try:
        response = _request(
            base_url,
            "POST",
            "/views",
            data=data,
            headers={"Content-Type": "application/json"},
        )
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if isinstance(response, dict):
        print("Created view:")
        print(f"  {response.get('id', '')} {response.get('name', '')}")
    return 0


def list_views(base_url: str, *, dry_run: bool = False, verbose: bool = False) -> int:
    """List all views on the VDI server.

    Args:
        base_url: Base URL of the VDI server.
        dry_run: If ``True``, print what would be done without contacting the server.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    if dry_run:
        print(f"dry-run: list views at {base_url}/views")
        return 0

    if verbose:
        print(f"Listing views at {base_url}/views")

    try:
        views = _get_views(base_url)
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Views:")
    for view in views:
        print(f"  {view.get('id', '')} {view.get('name', '')}")
    return 0


def delete_view(base_url: str, view_name: str, *, dry_run: bool = False, verbose: bool = False) -> int:
    """Delete a view by name from the VDI server.

    Args:
        base_url: Base URL of the VDI server.
        view_name: Name of the view to delete.
        dry_run: If ``True``, print what would be done without contacting the server.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    if dry_run:
        print(f"dry-run: delete view '{view_name}'")
        return 0

    if verbose:
        print(f"Looking up view '{view_name}' for deletion")

    try:
        view_id = _get_view_id_by_name(base_url, view_name)
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if view_id is None:
        print(f"View with the name '{view_name}' not found.")
        return 1

    try:
        response = _request(base_url, "DELETE", f"/views/{view_id}")
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(_extract_message(response))
    return 0


def list_files(base_url: str, view_name: str, *, dry_run: bool = False, verbose: bool = False) -> int:
    """List files in a view on the VDI server.

    Args:
        base_url: Base URL of the VDI server.
        view_name: Name of the view whose files should be listed.
        dry_run: If ``True``, print what would be done without contacting the server.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    if dry_run:
        print(f"dry-run: list files in view '{view_name}'")
        return 0

    if verbose:
        print(f"Listing files in view '{view_name}' at {base_url}/views/{view_name}/files")

    try:
        response = _request(base_url, "GET", f"/views/{view_name}/files")
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    files: JSONList
    if isinstance(response, list):
        files = response
    else:
        raw_files = response.get("files", [])
        files = cast(JSONList, raw_files) if isinstance(raw_files, list) else []

    if not files:
        print(f"The view '{view_name}' is empty.")
    else:
        print(f"Files in view '{view_name}':")
        for file_info in files:
            print(f"  {file_info.get('id', '')} {file_info.get('filename', '')}")
    return 0


def get_url(base_url: str, view_name: str, file_name: str) -> int:
    """Print the download URL for a file in a view.

    Args:
        base_url: Base URL of the VDI server.
        view_name: Name of the view containing the file.
        file_name: Name of the file.

    Returns:
        Exit code (always 0).
    """
    print(f"{base_url.rstrip('/')}/download/{view_name}/{file_name}")
    return 0


def remove_file(
    base_url: str,
    view_name: str,
    file_name: str,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Remove a file from a view on the VDI server.

    The ``file_name`` argument is used as the file ID (matching the bash
    script which passes the third argument directly as the file identifier).

    Args:
        base_url: Base URL of the VDI server.
        view_name: Name of the view containing the file.
        file_name: Identifier of the file to remove.
        dry_run: If ``True``, print what would be done without contacting the server.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    if dry_run:
        print(f"dry-run: remove file '{file_name}' from view '{view_name}'")
        return 0

    if verbose:
        print(f"Looking up view '{view_name}' for file removal")

    try:
        view_id = _get_view_id_by_name(base_url, view_name)
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if view_id is None:
        print(f"view '{view_name}' does not exist")
        return 1

    try:
        response = _request(base_url, "DELETE", f"/views/{view_id}/{file_name}")
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(_extract_message(response))
    return 0


def upload_file(
    base_url: str,
    view_name: str,
    file_path: str,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Upload a file to a view on the VDI server.

    Args:
        base_url: Base URL of the VDI server.
        view_name: Name of the view to upload to.
        file_path: Path to the file to upload.
        dry_run: If ``True``, print what would be done without contacting the server.
        verbose: If ``True``, print extra diagnostic information.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    path = Path(file_path)
    if not path.is_file():
        print(f"file '{file_path}' does not exist or is not a file")
        return 1

    if dry_run:
        print(f"dry-run: upload file '{file_path}' to view '{view_name}'")
        return 0

    if verbose:
        print(f"Looking up view '{view_name}' for file upload")

    try:
        view_id = _get_view_id_by_name(base_url, view_name)
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if view_id is None:
        print(f"view '{view_name}' does not exist")
        return 1

    # Build multipart/form-data body
    boundary = "----VDIBoundary"
    body_parts: list[bytes] = []

    # viewId field
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(b'Content-Disposition: form-data; name="viewId"\r\n\r\n')
    body_parts.append(f"{view_id}\r\n".encode())

    # files field
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(f'Content-Disposition: form-data; name="files"; filename="{path.name}"\r\n'.encode())
    body_parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
    body_parts.append(path.read_bytes())
    body_parts.append(b"\r\n")

    body_parts.append(f"--{boundary}--\r\n".encode())

    data = b"".join(body_parts)

    try:
        response = _request(
            base_url,
            "POST",
            f"/data/{view_name}",
            data=data,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
    except VDIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Response Message: {_extract_message(response)}")
    return 0
