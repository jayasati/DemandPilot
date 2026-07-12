"""Logging bootstrap.

Loads the dictConfig mapping from ``configs/logging.yaml``, resolves relative
log-file paths against the project root, and creates log directories before
handlers open them. See docs/LOGGING_STRATEGY.md.
"""

import logging.config
from pathlib import Path
from typing import Any

import yaml

from demandpilot.exceptions import ConfigError


def setup_logging(config_path: Path, root: Path) -> None:
    """Configure the logging system from a YAML dictConfig file.

    Args:
        config_path: Path to the logging YAML file (dictConfig schema).
        root: Project root used to resolve relative handler file paths.

    Raises:
        ConfigError: If the file is missing, unparsable, or rejected by
            ``logging.config.dictConfig``.
    """
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Logging config not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Logging config is not valid YAML: {config_path}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Logging config must be a mapping, got {type(raw).__name__}")
    config: dict[str, Any] = raw

    for handler in config.get("handlers", {}).values():
        filename = handler.get("filename")
        if filename is not None:
            path = Path(filename)
            if not path.is_absolute():
                path = root / path
            path.parent.mkdir(parents=True, exist_ok=True)
            handler["filename"] = str(path)

    try:
        logging.config.dictConfig(config)
    except (ValueError, TypeError, AttributeError, ImportError) as exc:
        raise ConfigError(f"Invalid logging configuration in {config_path}: {exc}") from exc
