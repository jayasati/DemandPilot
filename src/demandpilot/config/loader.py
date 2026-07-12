"""Loading and validation of the ``configs/`` directory."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from demandpilot.config.models import (
    AppConfig,
    CostsConfig,
    DemandPilotConfig,
    FeaturesConfig,
    ForecastConfig,
    SimulationConfig,
)
from demandpilot.exceptions import ConfigError

logger = logging.getLogger(__name__)

_ROOT_ENV_VAR = "DEMANDPILOT_ROOT"


def resolve_root(root: Path | None = None) -> Path:
    """Determine the project root used to resolve relative paths.

    Precedence: explicit argument, then the ``DEMANDPILOT_ROOT`` environment
    variable, then the current working directory.

    Args:
        root: Explicit project root, if the caller knows it.

    Returns:
        An absolute project root path.
    """
    if root is not None:
        return root.resolve()
    env_root = os.environ.get(_ROOT_ENV_VAR)
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd()


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file into a mapping, wrapping failures in ConfigError."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config file is not valid YAML: {path} ({exc})") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"Config file must contain a mapping, got {type(raw).__name__}: {path}")
    return raw


def load_config(root: Path | None = None) -> DemandPilotConfig:
    """Load and validate every configuration file under ``<root>/configs``.

    Args:
        root: Project root (see :func:`resolve_root` for defaulting rules).

    Returns:
        A frozen, fully validated configuration aggregate with all relative
        paths in ``app.paths`` resolved against the root.

    Raises:
        ConfigError: If any file is missing, unparsable, or invalid.
    """
    resolved_root = resolve_root(root)
    configs_dir = resolved_root / "configs"

    try:
        app = AppConfig(**_read_yaml(configs_dir / "app.yaml"))
        costs = CostsConfig(**_read_yaml(configs_dir / "costs.yaml"))
        features = FeaturesConfig(**_read_yaml(configs_dir / "features.yaml"))
        forecast = ForecastConfig(**_read_yaml(configs_dir / "forecast.yaml"))
        simulation = SimulationConfig(**_read_yaml(configs_dir / "simulation.yaml"))
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration under {configs_dir}:\n{exc}") from exc

    app = app.model_copy(update={"paths": app.paths.resolve_against(resolved_root)})
    logger.debug("Loaded configuration from %s", configs_dir)
    return DemandPilotConfig(
        root=resolved_root,
        app=app,
        costs=costs,
        features=features,
        forecast=forecast,
        simulation=simulation,
    )
