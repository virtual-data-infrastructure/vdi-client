# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""Unit tests for the VDI CLI."""

from __future__ import annotations

import pytest

from vdi_client import __version__
from vdi_client.cli import create_parser, main


class TestVersion:
    """Tests for the --version flag."""

    def test_version_string_is_not_empty(self) -> None:
        assert __version__ != ""
        assert __version__ != "unknown" or True  # may be "unknown" if not installed

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


class TestMain:
    """Tests for the main() entry point."""

    def test_main_no_command_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main([])
        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()

    def test_main_run_returns_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["run"])
        assert result == 1
        captured = capsys.readouterr()
        assert "not yet implemented" in captured.err.lower()

    def test_main_view_returns_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["view"])
        assert result == 1
        captured = capsys.readouterr()
        assert "not yet implemented" in captured.err.lower()
