# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""Unit tests for the VDI CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from vdi_client import __version__
from vdi_client.cli import create_parser, main


class TestVersion:
    """Tests for the --version flag."""

    def test_version_string_is_not_empty(self) -> None:
        assert __version__ != ""

    def test_version_flag_prints_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out


class TestParser:
    """Tests for the argument parser structure."""

    def test_parser_has_run_subcommand(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"

    def test_parser_has_view_subcommand(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["view"])
        assert args.command == "view"

    def test_parser_no_command_sets_command_to_none(self) -> None:
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None

    def test_parser_run_accepts_program_and_args(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["run", "python", "script.py", "--flag"])
        assert args.command == "run"
        assert args.program == "python"
        assert args.program_args == ["script.py", "--flag"]

    def test_parser_run_without_program(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"
        assert args.program is None

    def test_parser_run_accepts_common_args(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["run", "--dry-run", "-v", "--base-url", "http://example.com", "ls"])
        assert args.dry_run is True
        assert args.verbose is True
        assert args.base_url == "http://example.com"
        assert args.program == "ls"

    def test_parser_run_accepts_lib_override(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["run", "--lib", "/custom/path/libvdi.so", "ls"])
        assert args.lib == "/custom/path/libvdi.so"

    def test_parser_view_create(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["view", "create", "myview"])
        assert args.command == "view"
        assert args.subcommand == "create"
        assert args.view_name == "myview"

    def test_parser_view_list(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["view", "list"])
        assert args.command == "view"
        assert args.subcommand == "list"

    def test_parser_view_geturl(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["view", "geturl", "myview", "myfile"])
        assert args.subcommand == "geturl"
        assert args.view_name == "myview"
        assert args.file_name == "myfile"


class TestMain:
    """Tests for the main() entry point."""

    def test_main_no_command_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main([])
        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()

    def test_main_run_without_program_returns_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["run"])
        assert result == 1
        captured = capsys.readouterr()
        assert "no program" in captured.err.lower()

    def test_main_view_without_subcommand_returns_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "--base-url", "http://localhost"])
        assert result == 1
        captured = capsys.readouterr()
        assert "no view subcommand" in captured.err.lower()

    def test_main_view_without_base_url_returns_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "list"])
        assert result == 1
        captured = capsys.readouterr()
        assert "base_url" in captured.err.lower()


class TestMainViewDispatch:
    """Tests for view subcommand dispatch via main()."""

    def test_main_view_geturl(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "--base-url", "http://localhost", "geturl", "myview", "myfile"])
        assert result == 0
        captured = capsys.readouterr()
        assert "http://localhost/download/myview/myfile" in captured.out

    def test_main_view_geturl_without_base_url(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "geturl", "myview", "myfile"])
        assert result == 1
        captured = capsys.readouterr()
        assert "base_url" in captured.err.lower()

    def test_main_view_list_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "--base-url", "http://localhost", "list", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_main_view_create_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "--base-url", "http://localhost", "create", "myview", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_main_view_delete_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "--base-url", "http://localhost", "delete", "myview", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_main_view_files_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "--base-url", "http://localhost", "files", "myview", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_main_view_remove_dry_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view", "--base-url", "http://localhost", "remove", "myview", "file1", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_main_view_upload_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        file_path = tmp_path / "data.csv"
        file_path.write_text("a,b\n1,2\n")
        result = main(
            [
                "view",
                "--base-url",
                "http://localhost",
                "upload",
                "myview",
                str(file_path),
                "--dry-run",
            ]
        )
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out


class TestMainRunDispatch:
    """Tests for run subcommand dispatch via main()."""

    def test_main_run_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")
        result = main(["run", "--lib", str(lib), "--dry-run", "ls", "-la"])
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_main_run_no_program_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["run", "--dry-run"])
        assert result == 1
        captured = capsys.readouterr()
        assert "no program" in captured.err.lower()
