"""Tests for pure forecast evaluation metrics and quantile rearrangement."""

import numpy as np
import pytest

from demandpilot.core.metrics import (
    bias,
    coverage,
    enforce_monotonic_quantiles,
    pinball_loss,
    rmse,
    wape,
)


def _arr(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float64)


def test_pinball_loss_zero_for_perfect_prediction():
    y = _arr(1.0, 2.0, 3.0)
    assert pinball_loss(y, y, 0.5) == pytest.approx(0.0)


def test_pinball_loss_asymmetric_penalty():
    y_true = _arr(10.0)
    # Under-prediction by 5 at q=0.9 is penalized more than over-prediction by 5.
    under = pinball_loss(y_true, _arr(5.0), 0.9)
    over = pinball_loss(y_true, _arr(15.0), 0.9)
    assert under > over


def test_pinball_loss_matches_hand_calculation():
    y_true = _arr(10.0)
    y_pred = _arr(8.0)
    # diff = 2; q=0.1 -> max(0.1*2, -0.9*2) = max(0.2, -1.8) = 0.2
    assert pinball_loss(y_true, y_pred, 0.1) == pytest.approx(0.2)


def test_coverage_all_below_is_one():
    y_true = _arr(1.0, 2.0, 3.0)
    y_pred = _arr(10.0, 10.0, 10.0)
    assert coverage(y_true, y_pred) == pytest.approx(1.0)


def test_coverage_none_below_is_zero():
    y_true = _arr(10.0, 20.0, 30.0)
    y_pred = _arr(1.0, 1.0, 1.0)
    assert coverage(y_true, y_pred) == pytest.approx(0.0)


def test_coverage_half():
    y_true = _arr(1.0, 2.0, 3.0, 4.0)
    y_pred = _arr(5.0, 5.0, 0.0, 0.0)
    assert coverage(y_true, y_pred) == pytest.approx(0.5)


def test_wape_zero_for_perfect_prediction():
    y = _arr(1.0, 2.0, 3.0)
    assert wape(y, y) == pytest.approx(0.0)


def test_wape_matches_hand_calculation():
    y_true = _arr(10.0, 10.0)
    y_pred = _arr(8.0, 12.0)
    # sum|error| = 2 + 2 = 4; sum|actual| = 20 -> 0.2
    assert wape(y_true, y_pred) == pytest.approx(0.2)


def test_wape_nan_when_actuals_are_all_zero():
    y = _arr(0.0, 0.0)
    assert np.isnan(wape(y, _arr(1.0, 1.0)))


def test_bias_positive_when_overforecasting():
    y_true = _arr(10.0, 10.0)
    y_pred = _arr(12.0, 14.0)
    assert bias(y_true, y_pred) == pytest.approx(3.0)


def test_bias_negative_when_underforecasting():
    y_true = _arr(10.0, 10.0)
    y_pred = _arr(8.0, 6.0)
    assert bias(y_true, y_pred) == pytest.approx(-3.0)


def test_rmse_zero_for_perfect_prediction():
    y = _arr(1.0, 2.0, 3.0)
    assert rmse(y, y) == pytest.approx(0.0)


def test_rmse_matches_hand_calculation():
    y_true = _arr(0.0, 0.0)
    y_pred = _arr(3.0, 4.0)
    # sqrt(mean(9, 16)) = sqrt(12.5)
    assert rmse(y_true, y_pred) == pytest.approx(12.5**0.5)


def test_enforce_monotonic_quantiles_leaves_already_sorted_alone():
    predictions = {0.1: _arr(1.0, 2.0), 0.5: _arr(5.0, 6.0), 0.9: _arr(9.0, 10.0)}
    fixed = enforce_monotonic_quantiles(predictions)
    assert fixed[0.1].tolist() == [1.0, 2.0]
    assert fixed[0.5].tolist() == [5.0, 6.0]
    assert fixed[0.9].tolist() == [9.0, 10.0]


def test_enforce_monotonic_quantiles_fixes_crossing():
    # Row 0 crosses: p10=9 > p50=5 > p90=1. Rearrangement sorts to 1, 5, 9.
    predictions = {0.1: _arr(9.0), 0.5: _arr(5.0), 0.9: _arr(1.0)}
    fixed = enforce_monotonic_quantiles(predictions)
    assert fixed[0.1][0] <= fixed[0.5][0] <= fixed[0.9][0]
    assert sorted([fixed[0.1][0], fixed[0.5][0], fixed[0.9][0]]) == [1.0, 5.0, 9.0]


def test_enforce_monotonic_quantiles_preserves_quantile_keys():
    predictions = {0.25: _arr(1.0), 0.5: _arr(2.0), 0.75: _arr(3.0)}
    fixed = enforce_monotonic_quantiles(predictions)
    assert set(fixed) == {0.25, 0.5, 0.75}
