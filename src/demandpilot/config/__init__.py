"""Typed, validated configuration (ADR-009).

``load_config()`` is the single entry point: it reads every YAML file in
``configs/``, validates it into frozen Pydantic models, and fails fast with
:class:`~demandpilot.exceptions.ConfigError` on any missing file, parse error,
or invalid value. No other module reads configuration files directly.
"""

from demandpilot.config.loader import load_config, resolve_root
from demandpilot.config.models import (
    AppConfig,
    CostsConfig,
    DemandPilotConfig,
    FeaturesConfig,
    ForecastConfig,
    PathsConfig,
    SimulationConfig,
)

__all__ = [
    "AppConfig",
    "CostsConfig",
    "DemandPilotConfig",
    "FeaturesConfig",
    "ForecastConfig",
    "PathsConfig",
    "SimulationConfig",
    "load_config",
    "resolve_root",
]
