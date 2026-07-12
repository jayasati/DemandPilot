"""Tests for the logging bootstrap."""

import logging

import pytest

from demandpilot.exceptions import ConfigError
from demandpilot.logging_setup import setup_logging


def test_creates_log_dir_and_resolves_relative_path(tmp_path, reset_logging):
    config = tmp_path / "logging.yaml"
    config.write_text(
        """
version: 1
disable_existing_loggers: false
handlers:
  file:
    class: logging.FileHandler
    level: DEBUG
    filename: logs/test.log
root:
  level: INFO
  handlers: [file]
""",
        encoding="utf-8",
    )
    setup_logging(config, tmp_path)
    logging.getLogger("demandpilot.test").info("hello")
    assert (tmp_path / "logs" / "test.log").is_file()


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        setup_logging(tmp_path / "nope.yaml", tmp_path)


def test_non_mapping_yaml_raises(tmp_path):
    config = tmp_path / "logging.yaml"
    config.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        setup_logging(config, tmp_path)


def test_repo_logging_config_is_valid(repo_root, tmp_path, reset_logging):
    setup_logging(repo_root / "configs" / "logging.yaml", tmp_path)
    assert (tmp_path / "logs").is_dir()
