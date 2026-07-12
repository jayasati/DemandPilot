"""Pydantic models for every file under ``configs/``.

All models are frozen: configuration is immutable after loading. Validators
encode the constraints the domain requires (e.g. newsvendor economics must
yield a well-defined critical fractile — see ADR-012).
"""

from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from demandpilot.core.newsvendor import critical_fractile


class _FrozenModel(BaseModel):
    """Base for all config models: immutable, no unknown keys."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ProjectConfig(_FrozenModel):
    """Project identity block of ``app.yaml``."""

    name: str
    version: str
    environment: Literal["development", "staging", "production"]


class PathsConfig(_FrozenModel):
    """Filesystem layout. Relative paths are resolved against the project root."""

    data_dir: Path
    raw_data_dir: Path
    m5_raw_dir: Path
    processed_data_dir: Path
    snapshots_dir: Path
    reports_dir: Path
    logs_dir: Path
    configs_dir: Path
    sql_dir: Path
    duckdb_path: Path

    def resolve_against(self, root: Path) -> "PathsConfig":
        """Return a copy with every relative path resolved against ``root``."""
        resolved = {
            name: (value if value.is_absolute() else root / value)
            for name, value in self.__dict__.items()
        }
        return PathsConfig(**resolved)


class MlflowConfig(_FrozenModel):
    """MLflow tracking settings."""

    tracking_uri: str
    experiment_name: str


class StreamlitConfig(_FrozenModel):
    """Dashboard server settings."""

    host: str
    port: int = Field(ge=1, le=65535)


class AppConfig(_FrozenModel):
    """Contents of ``configs/app.yaml``."""

    project: ProjectConfig
    paths: PathsConfig
    mlflow: MlflowConfig
    streamlit: StreamlitConfig
    random_seed: int


class CostsConfig(_FrozenModel):
    """Contents of ``configs/costs.yaml``.

    M5 provides sell prices but not procurement costs, so economics are
    expressed as ratios of the unit sell price (documented assumptions —
    see ADR-012). All derived quantities are per unit of sell price.
    """

    currency: str
    unit_cost_ratio: float = Field(gt=0, lt=1)
    salvage_ratio: float = Field(ge=0, lt=1)
    holding_cost_ratio: float = Field(ge=0, lt=1)
    stockout_penalty_ratio: float = Field(ge=0)

    @model_validator(mode="after")
    def _salvage_below_cost(self) -> Self:
        """Reject salvage >= cost, which would make overstocking free or profitable."""
        if self.salvage_ratio >= self.unit_cost_ratio:
            raise ValueError(
                f"salvage_ratio ({self.salvage_ratio}) must be < "
                f"unit_cost_ratio ({self.unit_cost_ratio})"
            )
        return self

    @property
    def understock_cost_ratio(self) -> float:
        """Cost of one lost sale: forgone margin plus goodwill penalty."""
        return (1.0 - self.unit_cost_ratio) + self.stockout_penalty_ratio

    @property
    def overstock_cost_ratio(self) -> float:
        """Cost of one unsold unit: unrecovered cost plus holding."""
        return (self.unit_cost_ratio - self.salvage_ratio) + self.holding_cost_ratio

    @property
    def critical_fractile(self) -> float:
        """Optimal newsvendor service level implied by these economics."""
        return critical_fractile(self.understock_cost_ratio, self.overstock_cost_ratio)


class LagFeaturesConfig(_FrozenModel):
    """Lag feature block of ``features.yaml``."""

    column: str
    lags: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _positive_lags(self) -> Self:
        """Lags must be strictly positive: lag 0 is the target itself (leakage)."""
        if any(lag < 1 for lag in self.lags):
            raise ValueError(f"lags must all be >= 1, got {self.lags}")
        return self


class RollingFeaturesConfig(_FrozenModel):
    """Rolling-window feature block of ``features.yaml``."""

    column: str
    windows: list[int] = Field(min_length=1)
    aggregations: list[Literal["mean", "std", "min", "max", "sum"]] = Field(min_length=1)

    @model_validator(mode="after")
    def _positive_windows(self) -> Self:
        """Windows must span at least one row."""
        if any(window < 1 for window in self.windows):
            raise ValueError(f"windows must all be >= 1, got {self.windows}")
        return self


class FeaturesConfig(_FrozenModel):
    """Contents of ``configs/features.yaml``."""

    target: str
    date_column: str
    group_columns: list[str] = Field(min_length=1)
    lag_features: LagFeaturesConfig
    rolling_features: RollingFeaturesConfig
    calendar_features: list[str]
    categorical_features: list[str]
    numeric_features: list[str]


class TrainConfig(_FrozenModel):
    """Train/validation split block of ``forecast.yaml``."""

    test_size_days: int = Field(ge=1)
    validation_size_days: int = Field(ge=1)
    cv_folds: int = Field(ge=1)
    origin_stride_days: int = Field(ge=1)


class ModelConfig(_FrozenModel):
    """Model block of ``forecast.yaml``."""

    type: Literal["lightgbm"]
    objective: Literal["quantile"]
    params: dict[str, Any]
    early_stopping_rounds: int = Field(ge=1)


class ForecastMlflowConfig(_FrozenModel):
    """MLflow block of ``forecast.yaml``."""

    experiment_name: str
    register_model: bool
    model_name: str


class ForecastConfig(_FrozenModel):
    """Contents of ``configs/forecast.yaml``.

    Forecasts are probabilistic (P10/P50/P90 by default) and produced with a
    *direct* multi-horizon strategy — see ADR-008.
    """

    target_column: str
    date_column: str
    id_columns: list[str] = Field(min_length=1)
    horizon_days: int = Field(ge=1)
    frequency: Literal["D", "W", "M"]
    strategy: Literal["direct"]
    quantiles: list[float] = Field(min_length=1)
    metrics: list[Literal["pinball", "coverage", "wape", "bias", "rmse"]] = Field(min_length=1)
    train: TrainConfig
    model: ModelConfig
    mlflow: ForecastMlflowConfig

    @model_validator(mode="after")
    def _valid_quantiles(self) -> Self:
        """Quantiles must be strictly increasing in (0, 1) and include the median."""
        if any(not 0.0 < q < 1.0 for q in self.quantiles):
            raise ValueError(f"quantiles must lie strictly in (0, 1), got {self.quantiles}")
        if sorted(set(self.quantiles)) != self.quantiles:
            raise ValueError(f"quantiles must be strictly increasing, got {self.quantiles}")
        if 0.5 not in self.quantiles:
            raise ValueError("quantiles must include 0.5 (median point forecast)")
        return self


class SimulationConfig(_FrozenModel):
    """Contents of ``configs/simulation.yaml``."""

    policy: Literal["newsvendor"]
    service_level: float = Field(gt=0, lt=1)
    lead_time_days: int = Field(ge=0)
    review_period_days: int = Field(ge=1)
    demand_distribution: Literal["empirical", "normal", "poisson"]
    n_simulations: int = Field(ge=1)
    random_seed: int


class DemandPilotConfig(_FrozenModel):
    """Aggregate of all configuration files, with paths resolved to the root."""

    root: Path
    app: AppConfig
    costs: CostsConfig
    features: FeaturesConfig
    forecast: ForecastConfig
    simulation: SimulationConfig
