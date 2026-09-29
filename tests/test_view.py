# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""Unit tests for the ``view`` subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from vdi_client.view import (
    create_view,
    delete_view,
    get_url,
    list_files,
    list_views,
    remove_file,
    upload_file,
)


def _mock_response(body: str, status: int = 200) -> mock.MagicMock:
    """Create a mock urllib response object."""
    resp = mock.MagicMock()
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__ = mock.MagicMock(return_value=resp)
    resp.__exit__ = mock.MagicMock(return_value=False)
    resp.status = status
    return resp


class TestCreateView:
    """Tests for create_view()."""

    def test_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = create_view("http://localhost", "myview", dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert "myview" in captured.out

    def test_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        body = json.dumps({"id": 42, "name": "myview"})
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(body)):
            result = create_view("http://localhost", "myview")
        assert result == 0
        captured = capsys.readouterr()
        assert "Created view" in captured.out
        assert "42" in captured.out
        assert "myview" in captured.out

    def test_connection_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        import urllib.error

        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = create_view("http://localhost", "myview")
        assert result == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()


class TestListViews:
    """Tests for list_views()."""

    def test_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = list_views("http://localhost", dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        body = json.dumps([{"id": 1, "name": "view1"}, {"id": 2, "name": "view2"}])
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(body)):
            result = list_views("http://localhost")
        assert result == 0
        captured = capsys.readouterr()
        assert "Views:" in captured.out
        assert "view1" in captured.out
        assert "view2" in captured.out

    def test_empty_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("urllib.request.urlopen", return_value=_mock_response("[]")):
            result = list_views("http://localhost")
        assert result == 0
        captured = capsys.readouterr()
        assert "Views:" in captured.out


class TestDeleteView:
    """Tests for delete_view()."""

    def test_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = delete_view("http://localhost", "myview", dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        views_body = json.dumps([{"id": 5, "name": "myview"}])
        delete_body = json.dumps({"message": "View deleted successfully"})
        responses = [_mock_response(views_body), _mock_response(delete_body)]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = delete_view("http://localhost", "myview")
        assert result == 0
        captured = capsys.readouterr()
        assert "View deleted successfully" in captured.out

    def test_view_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        views_body = json.dumps([{"id": 5, "name": "other"}])
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(views_body)):
            result = delete_view("http://localhost", "nonexistent")
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()


class TestListFiles:
    """Tests for list_files()."""

    def test_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = list_files("http://localhost", "myview", dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_success_with_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        body = json.dumps([{"id": 1, "filename": "data.csv"}, {"id": 2, "filename": "plot.png"}])
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(body)):
            result = list_files("http://localhost", "myview")
        assert result == 0
        captured = capsys.readouterr()
        assert "Files in view" in captured.out
        assert "data.csv" in captured.out

    def test_empty_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("urllib.request.urlopen", return_value=_mock_response("[]")):
            result = list_files("http://localhost", "myview")
        assert result == 0
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower()

    def test_success_with_dict_wrapper(self, capsys: pytest.CaptureFixture[str]) -> None:
        body = json.dumps({"files": [{"id": 1, "filename": "data.csv"}]})
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(body)):
            result = list_files("http://localhost", "myview")
        assert result == 0
        captured = capsys.readouterr()
        assert "data.csv" in captured.out


class TestGetUrl:
    """Tests for get_url()."""

    def test_prints_url(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = get_url("http://localhost", "myview", "myfile.csv")
        assert result == 0
        captured = capsys.readouterr()
        assert "http://localhost/download/myview/myfile.csv" in captured.out

    def test_strips_trailing_slash(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = get_url("http://localhost/", "myview", "myfile.csv")
        assert result == 0
        captured = capsys.readouterr()
        assert "http://localhost/download/myview/myfile.csv" in captured.out


class TestRemoveFile:
    """Tests for remove_file()."""

    def test_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = remove_file("http://localhost", "myview", "file1", dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        views_body = json.dumps([{"id": 5, "name": "myview"}])
        delete_body = json.dumps({"message": "File removed"})
        responses = [_mock_response(views_body), _mock_response(delete_body)]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = remove_file("http://localhost", "myview", "file1")
        assert result == 0
        captured = capsys.readouterr()
        assert "File removed" in captured.out

    def test_view_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        views_body = json.dumps([{"id": 5, "name": "other"}])
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(views_body)):
            result = remove_file("http://localhost", "nonexistent", "file1")
        assert result == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.out.lower()


class TestUploadFile:
    """Tests for upload_file()."""

    def test_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        file_path = tmp_path / "data.csv"
        file_path.write_text("a,b,c\n1,2,3\n")
        result = upload_file("http://localhost", "myview", str(file_path), dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = upload_file("http://localhost", "myview", "/nonexistent/file.csv")
        assert result == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.out.lower()

    def test_success(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        file_path = tmp_path / "data.csv"
        file_path.write_text("a,b,c\n1,2,3\n")
        views_body = json.dumps([{"id": 5, "name": "myview"}])
        upload_body = json.dumps({"message": "File uploaded"})
        responses = [_mock_response(views_body), _mock_response(upload_body)]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = upload_file("http://localhost", "myview", str(file_path))
        assert result == 0
        captured = capsys.readouterr()
        assert "File uploaded" in captured.out

    def test_view_not_found(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        file_path = tmp_path / "data.csv"
        file_path.write_text("a,b,c\n1,2,3\n")
        views_body = json.dumps([{"id": 5, "name": "other"}])
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(views_body)):
            result = upload_file("http://localhost", "nonexistent", str(file_path))
        assert result == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.out.lower()


class TestViewErrorPaths:
    """Tests for error handling in view subcommands."""

    def test_list_views_connection_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        import urllib.error

        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = list_views("http://localhost")
        assert result == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_list_files_connection_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        import urllib.error

        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = list_files("http://localhost", "myview")
        assert result == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_delete_view_connection_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        import urllib.error

        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = delete_view("http://localhost", "myview")
        assert result == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_remove_file_connection_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        import urllib.error

        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = remove_file("http://localhost", "myview", "file1")
        assert result == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_upload_file_connection_error(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        import urllib.error

        file_path = tmp_path / "data.csv"
        file_path.write_text("a,b\n1,2\n")
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = upload_file("http://localhost", "myview", str(file_path))
        assert result == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_create_view_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        body = json.dumps({"id": 1, "name": "myview"})
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(body)):
            result = create_view("http://localhost", "myview", verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Creating view" in captured.out

    def test_list_views_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        body = json.dumps([{"id": 1, "name": "view1"}])
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(body)):
            result = list_views("http://localhost", verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Listing views" in captured.out

    def test_delete_view_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        views_body = json.dumps([{"id": 5, "name": "myview"}])
        delete_body = json.dumps({"message": "deleted"})
        responses = [_mock_response(views_body), _mock_response(delete_body)]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = delete_view("http://localhost", "myview", verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Looking up" in captured.out

    def test_list_files_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        body = json.dumps([{"id": 1, "filename": "data.csv"}])
        with mock.patch("urllib.request.urlopen", return_value=_mock_response(body)):
            result = list_files("http://localhost", "myview", verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Listing files" in captured.out

    def test_remove_file_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        views_body = json.dumps([{"id": 5, "name": "myview"}])
        delete_body = json.dumps({"message": "removed"})
        responses = [_mock_response(views_body), _mock_response(delete_body)]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = remove_file("http://localhost", "myview", "file1", verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Looking up" in captured.out

    def test_upload_file_verbose(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        file_path = tmp_path / "data.csv"
        file_path.write_text("a,b\n1,2\n")
        views_body = json.dumps([{"id": 5, "name": "myview"}])
        upload_body = json.dumps({"message": "uploaded"})
        responses = [_mock_response(views_body), _mock_response(upload_body)]
        with mock.patch("urllib.request.urlopen", side_effect=responses):
            result = upload_file("http://localhost", "myview", str(file_path), verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Looking up" in captured.out
