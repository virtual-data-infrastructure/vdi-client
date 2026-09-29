# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""Unit tests for the ``run`` subcommand."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from vdi_client.run import resolve_lib_path, run


class TestResolveLibPath:
    """Tests for resolve_lib_path()."""

    def test_explicit_override(self, tmp_path: Path) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")
        result = resolve_lib_path(str(lib))
        assert result == lib.resolve()

    def test_env_var_used_when_no_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")
        monkeypatch.setenv("VDI_LIB_PATH", str(lib))
        result = resolve_lib_path(None)
        assert result == lib.resolve()

    def test_override_takes_precedence_over_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_lib = tmp_path / "env_lib.so"
        env_lib.write_text("dummy")
        override_lib = tmp_path / "override_lib.so"
        override_lib.write_text("dummy")
        monkeypatch.setenv("VDI_LIB_PATH", str(env_lib))
        result = resolve_lib_path(str(override_lib))
        assert result == override_lib.resolve()

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="VDI shared library not found"):
            resolve_lib_path(str(tmp_path / "nonexistent.so"))


class TestRun:
    """Tests for run()."""

    def test_run_without_program_returns_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = run(None, [], dry_run=True)
        assert result == 1
        captured = capsys.readouterr()
        assert "no program" in captured.err.lower()

    def test_run_dry_run_prints_command(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")
        result = run("ls", ["-la"], lib_override=str(lib), dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert "ls" in captured.out

    def test_run_dry_run_verbose_prints_lib_path(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")
        result = run("ls", [], lib_override=str(lib), dry_run=True, verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "LD_PRELOAD" in captured.out

    def test_run_missing_lib_returns_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        result = run("ls", [], lib_override=str(tmp_path / "nonexistent.so"), dry_run=True)
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_run_execvpe_called(
        self,
        tmp_path: Path,
    ) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")

        with mock.patch("os.execvpe") as mock_exec:
            run("ls", ["-la"], lib_override=str(lib))

        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        assert call_args[0][0] == "ls"
        assert call_args[0][1] == ["ls", "-la"]
        assert call_args[0][2]["LD_PRELOAD"] == str(lib.resolve())

    def test_run_execvpe_failure_returns_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")

        with mock.patch("os.execvpe", side_effect=OSError("No such file")):
            result = run("nonexistent-program", [], lib_override=str(lib))

        assert result == 1
        captured = capsys.readouterr()
        assert "failed to execute" in captured.err.lower()

    def test_run_verbose_prints_before_exec(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        lib = tmp_path / "libvdi.so"
        lib.write_text("dummy")

        with mock.patch("os.execvpe"):
            run("ls", [], lib_override=str(lib), verbose=True)

        captured = capsys.readouterr()
        assert "LD_PRELOAD" in captured.out
