"""Tests for configuration models and the loader."""

import pytest
import yaml
from pydantic import ValidationError

from demandpilot.config import CostsConfig, ForecastConfig, load_config
from demandpilot.config.models import SimulationConfig
from demandpilot.exceptions import ConfigError


def test_repo_configs_load_and_validate(repo_root):
    config = load_config(repo_root)
    assert config.root == repo_root
    assert config.app.project.name == "DemandPilot"
    # Paths are resolved to absolute against the root.
    assert config.app.paths.duckdb_path.is_absolute()
    assert config.app.paths.sql_dir == repo_root / "sql"
    # The probabilistic contract holds.
    assert 0.5 in config.forecast.quantiles
    assert config.forecast.strategy == "direct"
    assert 0.0 < config.costs.critical_fractile < 1.0


def test_missing_configs_dir_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path)


def test_invalid_yaml_raises(tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "app.yaml").write_text("project: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_config(tmp_path)


def test_costs_salvage_above_cost_rejected():
    with pytest.raises(ValidationError, match="salvage_ratio"):
        CostsConfig(
            currency="USD",
            unit_cost_ratio=0.5,
            salvage_ratio=0.6,
            holding_cost_ratio=0.01,
            stockout_penalty_ratio=0.0,
        )


def test_costs_critical_fractile_matches_hand_calculation():
    costs = CostsConfig(
        currency="USD",
        unit_cost_ratio=0.65,
        salvage_ratio=0.35,
        holding_cost_ratio=0.02,
        stockout_penalty_ratio=0.10,
    )
    cu = (1 - 0.65) + 0.10
    co = (0.65 - 0.35) + 0.02
    assert costs.understock_cost_ratio == pytest.approx(cu)
    assert costs.overstock_cost_ratio == pytest.approx(co)
    assert costs.critical_fractile == pytest.approx(cu / (cu + co))


@pytest.mark.parametrize(
    "quantiles",
    [
        [0.1, 0.9],  # median missing
        [0.5, 0.1, 0.9],  # not increasing
        [0.0, 0.5, 0.9],  # 0 not allowed
        [0.1, 0.5, 1.0],  # 1 not allowed
        [0.1, 0.1, 0.5],  # duplicates
    ],
)
def test_forecast_invalid_quantiles_rejected(repo_root, quantiles):
    raw = yaml.safe_load((repo_root / "configs" / "forecast.yaml").read_text(encoding="utf-8"))
    raw["quantiles"] = quantiles
    with pytest.raises(ValidationError):
        ForecastConfig(**raw)


def test_forecast_regression_objective_rejected(repo_root):
    raw = yaml.safe_load((repo_root / "configs" / "forecast.yaml").read_text(encoding="utf-8"))
    raw["model"]["objective"] = "regression"  # point forecasts violate the contract
    with pytest.raises(ValidationError):
        ForecastConfig(**raw)


def test_simulation_zero_lead_time_rejected(repo_root):
    """lead_time_days=0 would self-join a row to itself (leakage) — must be >= 1."""
    raw = yaml.safe_load((repo_root / "configs" / "simulation.yaml").read_text(encoding="utf-8"))
    raw["lead_time_days"] = 0
    with pytest.raises(ValidationError, match="lead_time_days"):
        SimulationConfig(**raw)
