"""Quantile LightGBM forecaster.

One model per quantile, trained on the same feature matrix, with post-hoc
monotonic rearrangement to guard against quantile crossing (see
``demandpilot.core.metrics.enforce_monotonic_quantiles``). Polars is used
everywhere except immediately before the LightGBM call, where frames are
converted to pandas (ADR-007 — pandas only at library boundaries).
"""

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
import polars as pl

from demandpilot.config.models import ModelConfig
from demandpilot.core.metrics import FloatArray, enforce_monotonic_quantiles

_NON_FEATURE_COLUMNS = frozenset({"origin_date", "target_date", "target"})


@dataclass(frozen=True)
class QuantileModel:
    """A single trained quantile model plus the exact feature columns it saw."""

    quantile: float
    booster: lgb.LGBMRegressor
    feature_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]


class QuantileForecaster:
    """Trains and predicts one LightGBM model per quantile."""

    def __init__(self, model_config: ModelConfig, categorical_columns: tuple[str, ...]) -> None:
        """Create a forecaster.

        Args:
            model_config: LightGBM hyperparameters and early-stopping config.
            categorical_columns: Feature columns to treat as categorical.
        """
        self._model_config = model_config
        self._categorical_columns = categorical_columns

    def fit(
        self, train: pl.DataFrame, validation: pl.DataFrame, quantiles: list[float]
    ) -> list[QuantileModel]:
        """Fit one model per quantile with early stopping on ``validation``.

        Args:
            train: Training partition, including a ``target`` column.
            validation: Validation partition used for early stopping.
            quantiles: Quantile levels to train (in (0, 1)).

        Returns:
            One fitted model per quantile.
        """
        feature_columns = tuple(col for col in train.columns if col not in _NON_FEATURE_COLUMNS)
        x_train = self._to_pandas(train, feature_columns)
        y_train = train["target"].to_numpy()
        x_val = self._to_pandas(validation, feature_columns)
        y_val = validation["target"].to_numpy()

        models = []
        for quantile in quantiles:
            regressor = lgb.LGBMRegressor(
                objective="quantile", alpha=quantile, **self._model_config.params
            )
            regressor.fit(
                x_train,
                y_train,
                eval_set=[(x_val, y_val)],
                categorical_feature=list(self._categorical_columns) or "auto",
                callbacks=[
                    lgb.early_stopping(self._model_config.early_stopping_rounds, verbose=False)
                ],
            )
            models.append(
                QuantileModel(
                    quantile=quantile,
                    booster=regressor,
                    feature_columns=feature_columns,
                    categorical_columns=self._categorical_columns,
                )
            )
        return models

    def predict(self, models: list[QuantileModel], data: pl.DataFrame) -> dict[float, FloatArray]:
        """Predict every quantile for ``data``, then enforce monotonicity.

        Args:
            models: Models returned by :meth:`fit`.
            data: Rows to predict, containing every model's feature columns.

        Returns:
            Mapping of quantile level to its (monotonic-corrected) predictions.
        """
        raw: dict[float, FloatArray] = {}
        for model in models:
            x = self._to_pandas(data, model.feature_columns)
            raw[model.quantile] = np.asarray(model.booster.predict(x), dtype=np.float64)
        return enforce_monotonic_quantiles(raw)

    def _to_pandas(self, data: pl.DataFrame, feature_columns: tuple[str, ...]) -> pd.DataFrame:
        """Convert to pandas at the LightGBM boundary, with categorical dtypes set."""
        frame = data.select(list(feature_columns)).to_pandas()
        for col in self._categorical_columns:
            if col in frame.columns:
                frame[col] = frame[col].astype("category")
        return frame
