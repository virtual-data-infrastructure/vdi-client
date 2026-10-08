# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""Unit tests for the ``log`` subcommand."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from vdi_client.log import (
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_PREFIX,
    clean_logs,
    collect_log_entries,
    list_logs,
    resolve_log_dir,
    resolve_log_prefix,
    show_log,
)

# --- Sample log line matching the wrapper's format ---
# Columns (space-separated): timestamp, hostinfo, user, home, pid, ppid,
# pgid, cwd, program_path, cmdline, start_time, elapsed, func, args...
SAMPLE_LOG_LINE = (
    "1736344161::2025-01-08+13:49:21+UTC "
    "nextflow.novalocal//FQHN_ERROR//IPv4%%lo%%127.0.0.1 "
    "almalinux /home/almalinux 55715 18260 55715 "
    "/home/almalinux/data-graph/src/ld-preload "
    "/cvmfs/software.eessi.io/.../python3.11 "
    "python%%examples/map_plot.py%%data/no.json%%--out%%outputs "
    "1736344160%%2025-01-08+13:49:20+UTC 39057 open64 "
    "/home/almalinux/data-graph/src/ld-preload/examples/map_plot.py "
    "524288::O_RDONLY 438::0666"
)


def _create_log(log_dir: Path, pid: int, content: str | None = None, prefix: str = DEFAULT_LOG_PREFIX) -> Path:
    """Create a log file in *log_dir* with the given PID."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{prefix}{pid}.log"
    path.write_text(content if content is not None else SAMPLE_LOG_LINE + "\n")
    return path


class TestResolveLogDir:
    """Tests for resolve_log_dir()."""

    def test_explicit_override(self, tmp_path: Path) -> None:
        result = resolve_log_dir(str(tmp_path))
        assert result == tmp_path

    def test_env_var_used_when_no_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDI_LOG_DIR", str(tmp_path))
        result = resolve_log_dir(None)
        assert result == tmp_path

    def test_override_takes_precedence_over_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        override_dir = tmp_path / "override"
        override_dir.mkdir()
        monkeypatch.setenv("VDI_LOG_DIR", str(env_dir))
        result = resolve_log_dir(str(override_dir))
        assert result == override_dir

    def test_default_when_nothing_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDI_LOG_DIR", raising=False)
        result = resolve_log_dir(None)
        assert result == DEFAULT_LOG_DIR


class TestResolveLogPrefix:
    """Tests for resolve_log_prefix()."""

    def test_explicit_override(self) -> None:
        assert resolve_log_prefix("custom.") == "custom."

    def test_env_var_used_when_no_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDI_LOG_FILE_PREFIX", "mylog.")
        assert resolve_log_prefix(None) == "mylog."

    def test_default_when_nothing_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDI_LOG_FILE_PREFIX", raising=False)
        assert resolve_log_prefix(None) == DEFAULT_LOG_PREFIX


class TestCollectLogEntries:
    """Tests for collect_log_entries()."""

    def test_collects_matching_files(self, tmp_path: Path) -> None:
        _create_log(tmp_path, 100)
        _create_log(tmp_path, 200)
        entries = collect_log_entries(tmp_path, DEFAULT_LOG_PREFIX)
        pids = {e.pid for e in entries}
        assert pids == {100, 200}

    def test_ignores_non_matching_files(self, tmp_path: Path) -> None:
        _create_log(tmp_path, 100)
        (tmp_path / "other.txt").write_text("not a log")
        entries = collect_log_entries(tmp_path, DEFAULT_LOG_PREFIX)
        assert len(entries) == 1
        assert entries[0].pid == 100

    def test_ignores_subdirectories(self, tmp_path: Path) -> None:
        _create_log(tmp_path, 100)
        (tmp_path / "vdi_log_subdir.log").mkdir()
        entries = collect_log_entries(tmp_path, DEFAULT_LOG_PREFIX)
        assert len(entries) == 1

    def test_returns_empty_for_nonexistent_dir(self, tmp_path: Path) -> None:
        entries = collect_log_entries(tmp_path / "nonexistent", DEFAULT_LOG_PREFIX)
        assert entries == []

    def test_parses_program_name(self, tmp_path: Path) -> None:
        _create_log(tmp_path, 100)
        entries = collect_log_entries(tmp_path, DEFAULT_LOG_PREFIX)
        assert len(entries) == 1
        assert entries[0].program == "python"

    def test_program_is_none_for_empty_file(self, tmp_path: Path) -> None:
        _create_log(tmp_path, 100, content="")
        entries = collect_log_entries(tmp_path, DEFAULT_LOG_PREFIX)
        assert len(entries) == 1
        assert entries[0].program is None

    def test_custom_prefix(self, tmp_path: Path) -> None:
        _create_log(tmp_path, 100, prefix="mylog.")
        (tmp_path / "vdi_log.100.log").write_text("should not match\n")
        entries = collect_log_entries(tmp_path, "mylog.")
        assert len(entries) == 1
        assert entries[0].pid == 100

    def test_populates_size_and_mtime(self, tmp_path: Path) -> None:
        path = _create_log(tmp_path, 100)
        entries = collect_log_entries(tmp_path, DEFAULT_LOG_PREFIX)
        assert len(entries) == 1
        assert entries[0].size == path.stat().st_size
        assert entries[0].mtime == path.stat().st_mtime


class TestListLogs:
    """Tests for list_logs()."""

    def test_list_empty_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        result = list_logs(log_dir_override=str(tmp_path))
        assert result == 0
        captured = capsys.readouterr()
        assert "No log files" in captured.out

    def test_list_nonexistent_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        result = list_logs(log_dir_override=str(tmp_path / "nope"))
        assert result == 0
        captured = capsys.readouterr()
        assert "No log directory" in captured.out

    def test_list_short_format(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        _create_log(tmp_path, 200)
        result = list_logs(log_dir_override=str(tmp_path))
        assert result == 0
        captured = capsys.readouterr()
        assert "vdi_log.100.log" in captured.out
        assert "vdi_log.200.log" in captured.out

    def test_list_long_format(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        result = list_logs(log_dir_override=str(tmp_path), long_format=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "PID" in captured.out
        assert "Size" in captured.out
        assert "Modified" in captured.out
        assert "Program" in captured.out
        assert "python" in captured.out

    def test_list_sort_by_pid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 300)
        _create_log(tmp_path, 100)
        _create_log(tmp_path, 200)
        result = list_logs(log_dir_override=str(tmp_path), sort_key="pid")
        assert result == 0
        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line.strip()]
        pids = [int(line.split()[0]) for line in lines]
        assert pids == [100, 200, 300]

    def test_list_sort_by_pid_reverse(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 300)
        _create_log(tmp_path, 100)
        _create_log(tmp_path, 200)
        result = list_logs(log_dir_override=str(tmp_path), sort_key="pid", reverse=True)
        assert result == 0
        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line.strip()]
        pids = [int(line.split()[0]) for line in lines]
        assert pids == [300, 200, 100]

    def test_list_sort_by_size(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100, content="short\n")
        _create_log(tmp_path, 200, content="x" * 1000 + "\n")
        result = list_logs(log_dir_override=str(tmp_path), sort_key="size")
        assert result == 0
        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line.strip()]
        pids = [int(line.split()[0]) for line in lines]
        assert pids == [100, 200]

    def test_list_sort_by_date(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        old = _create_log(tmp_path, 100)
        new = _create_log(tmp_path, 200)
        os.utime(old, (time.time() - 100, time.time() - 100))
        os.utime(new, (time.time(), time.time()))
        result = list_logs(log_dir_override=str(tmp_path), sort_key="date")
        assert result == 0
        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line.strip()]
        pids = [int(line.split()[0]) for line in lines]
        assert pids == [100, 200]

    def test_list_sort_by_program(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100, content=SAMPLE_LOG_LINE.replace("python%%", "zzz%%"))
        _create_log(tmp_path, 200, content=SAMPLE_LOG_LINE.replace("python%%", "aaa%%"))
        result = list_logs(log_dir_override=str(tmp_path), sort_key="program")
        assert result == 0
        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line.strip()]
        pids = [int(line.split()[0]) for line in lines]
        assert pids == [200, 100]

    def test_list_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        result = list_logs(log_dir_override=str(tmp_path), dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert "vdi_log.100.log" not in captured.out

    def test_list_verbose(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        result = list_logs(log_dir_override=str(tmp_path), verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Listing" in captured.out


class TestShowLog:
    """Tests for show_log()."""

    def test_show_existing_log(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100, content="line1\nline2\n")
        result = show_log(100, log_dir_override=str(tmp_path))
        assert result == 0
        captured = capsys.readouterr()
        assert "line1" in captured.out
        assert "line2" in captured.out

    def test_show_nonexistent_log(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        result = show_log(999, log_dir_override=str(tmp_path))
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_show_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100, content="content\n")
        result = show_log(100, log_dir_override=str(tmp_path), dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert "content" not in captured.out

    def test_show_verbose(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100, content="content\n")
        result = show_log(100, log_dir_override=str(tmp_path), verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Showing" in captured.out

    def test_show_with_custom_prefix(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100, prefix="mylog.", content="custom\n")
        result = show_log(100, log_dir_override=str(tmp_path), log_prefix_override="mylog.")
        assert result == 0
        captured = capsys.readouterr()
        assert "custom" in captured.out


class TestCleanLogs:
    """Tests for clean_logs()."""

    def test_clean_all(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        _create_log(tmp_path, 200)
        result = clean_logs(log_dir_override=str(tmp_path))
        assert result == 0
        captured = capsys.readouterr()
        assert "Removed 2 log file(s)" in captured.out
        assert not (tmp_path / "vdi_log.100.log").exists()
        assert not (tmp_path / "vdi_log.200.log").exists()

    def test_clean_specific_pid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        _create_log(tmp_path, 200)
        result = clean_logs(pid=100, log_dir_override=str(tmp_path))
        assert result == 0
        captured = capsys.readouterr()
        assert "Removed" in captured.out
        assert not (tmp_path / "vdi_log.100.log").exists()
        assert (tmp_path / "vdi_log.200.log").exists()

    def test_clean_nonexistent_pid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        result = clean_logs(pid=999, log_dir_override=str(tmp_path))
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()
        assert (tmp_path / "vdi_log.100.log").exists()

    def test_clean_empty_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        result = clean_logs(log_dir_override=str(tmp_path))
        assert result == 0
        captured = capsys.readouterr()
        assert "No log files" in captured.out

    def test_clean_nonexistent_dir(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        result = clean_logs(log_dir_override=str(tmp_path / "nope"))
        assert result == 0
        captured = capsys.readouterr()
        assert "No log directory" in captured.out

    def test_clean_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        _create_log(tmp_path, 200)
        result = clean_logs(log_dir_override=str(tmp_path), dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert "2 log file(s)" in captured.out
        assert (tmp_path / "vdi_log.100.log").exists()
        assert (tmp_path / "vdi_log.200.log").exists()

    def test_clean_specific_pid_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        result = clean_logs(pid=100, log_dir_override=str(tmp_path), dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out
        assert (tmp_path / "vdi_log.100.log").exists()

    def test_clean_verbose(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100)
        result = clean_logs(log_dir_override=str(tmp_path), verbose=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Removing" in captured.out
        assert "removed:" in captured.out

    def test_clean_with_custom_prefix(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        _create_log(tmp_path, 100, prefix="mylog.")
        _create_log(tmp_path, 200, prefix=DEFAULT_LOG_PREFIX)
        result = clean_logs(log_dir_override=str(tmp_path), log_prefix_override="mylog.")
        assert result == 0
        captured = capsys.readouterr()
        assert "Removed 1 log file(s)" in captured.out
        assert not (tmp_path / "mylog.100.log").exists()
        assert (tmp_path / "vdi_log.200.log").exists()
