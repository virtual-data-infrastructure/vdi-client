# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors
"""Unit tests for VDI configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from vdi_client.config import DEFAULT_CONFIG_PATH, load_config, resolve_base_url


class TestLoadConfig:
    """Tests for load_config()."""

    def test_load_config_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_config(tmp_path / "nonexistent")
        assert result == {}

    def test_load_config_parses_key_value(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("BASE_URL=http://example.com\n")
        result = load_config(config_file)
        assert result == {"BASE_URL": "http://example.com"}

    def test_load_config_strips_quotes(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("BASE_URL=\"http://example.com\"\nOTHER='hello'\n")
        result = load_config(config_file)
        assert result == {"BASE_URL": "http://example.com", "OTHER": "hello"}

    def test_load_config_ignores_comments(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("# this is a comment\nBASE_URL=http://example.com\n# another\n")
        result = load_config(config_file)
        assert result == {"BASE_URL": "http://example.com"}

    def test_load_config_ignores_blank_lines(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("\n\nBASE_URL=http://example.com\n\n")
        result = load_config(config_file)
        assert result == {"BASE_URL": "http://example.com"}

    def test_load_config_ignores_lines_without_equals(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("not a config line\nBASE_URL=http://example.com\n")
        result = load_config(config_file)
        assert result == {"BASE_URL": "http://example.com"}

    def test_load_config_multiple_keys(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("BASE_URL=http://example.com\nDEBUG=1\nLOG_FILE=/tmp/log\n")
        result = load_config(config_file)
        assert result == {
            "BASE_URL": "http://example.com",
            "DEBUG": "1",
            "LOG_FILE": "/tmp/log",
        }

    def test_load_config_strips_whitespace(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("  BASE_URL  =  http://example.com  \n")
        result = load_config(config_file)
        assert result == {"BASE_URL": "http://example.com"}

    def test_default_config_path(self) -> None:
        assert Path.home() / ".vdi" / "config" == DEFAULT_CONFIG_PATH


class TestResolveBaseUrl:
    """Tests for resolve_base_url()."""

    def test_cli_base_url_takes_precedence(self) -> None:
        result = resolve_base_url("http://cli.example.com", {"BASE_URL": "http://config.example.com"})
        assert result == "http://cli.example.com"

    def test_config_base_url_used_when_no_cli(self) -> None:
        result = resolve_base_url(None, {"BASE_URL": "http://config.example.com"})
        assert result == "http://config.example.com"

    def test_env_base_url_used_when_no_cli_or_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BASE_URL", "http://env.example.com")
        result = resolve_base_url(None, {})
        assert result == "http://env.example.com"

    def test_returns_none_when_nothing_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BASE_URL", raising=False)
        result = resolve_base_url(None, {})
        assert result is None

    def test_cli_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BASE_URL", "http://env.example.com")
        result = resolve_base_url("http://cli.example.com", {})
        assert result == "http://cli.example.com"

    def test_config_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BASE_URL", "http://env.example.com")
        result = resolve_base_url(None, {"BASE_URL": "http://config.example.com"})
        assert result == "http://config.example.com"
