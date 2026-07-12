"""Pure forecast evaluation metrics and quantile-crossing correction.

No I/O, no configuration, no framework imports — see docs/ARCHITECTURE.md.
"""

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def pinball_loss(y_true: FloatArray, y_pred: FloatArray, quantile: float) -> float:
    """Mean pinball (quantile) loss at the given quantile level.

    Args:
        y_true: Actual values.
        y_pred: Predicted values targeting ``quantile``.
        quantile: The quantile level in (0, 1) that ``y_pred`` targets.

    Returns:
        The mean pinball loss (lower is better; 0 is a perfect fit).
    """
    diff = y_true - y_pred
    return float(np.mean(np.maximum(quantile * diff, (quantile - 1) * diff)))


def coverage(y_true: FloatArray, y_pred: FloatArray) -> float:
    """Empirical fraction of actuals at or below the prediction.

    Compare against the nominal quantile level to check calibration: a
    well-calibrated P90 model should have coverage close to 0.9.
    """
    return float(np.mean(y_true <= y_pred))


def wape(y_true: FloatArray, y_pred: FloatArray) -> float:
    """Weighted absolute percentage error: sum of absolute error over sum of actuals."""
    denominator = float(np.sum(np.abs(y_true)))
    if denominator == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred))) / denominator


def bias(y_true: FloatArray, y_pred: FloatArray) -> float:
    """Mean signed error: positive means the model over-forecasts on average."""
    return float(np.mean(y_pred - y_true))


def rmse(y_true: FloatArray, y_pred: FloatArray) -> float:
    """Root mean squared error."""
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def enforce_monotonic_quantiles(predictions: dict[float, FloatArray]) -> dict[float, FloatArray]:
    """Rearrange per-row quantile predictions to be non-decreasing in quantile order.

    Independently trained quantile models can "cross" (e.g. a row's P10
    prediction exceeding its P90) — see docs/KNOWN_LIMITATIONS.md. This applies
    the standard rearrangement fix (Chernozhukov, Fernandez-Val & Galichon,
    2010): sort each row's predicted values ascending and reassign them to
    quantiles in ascending order, the closest monotonic-consistent adjustment.

    Args:
        predictions: Mapping of quantile level to its predicted array (all
            arrays the same length, aligned row-for-row).

    Returns:
        A new mapping with the same keys, values rearranged to be monotonic.
    """
    ordered_quantiles = sorted(predictions)
    stacked = np.stack([predictions[q] for q in ordered_quantiles], axis=1)
    sorted_stacked = np.sort(stacked, axis=1)
    return {q: sorted_stacked[:, i] for i, q in enumerate(ordered_quantiles)}
