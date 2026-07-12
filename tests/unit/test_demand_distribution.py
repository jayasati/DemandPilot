"""Tests for the classical demand-distribution quantile estimators."""

import numpy as np
import pytest

from demandpilot.core.demand_distribution import (
    empirical_bootstrap_quantile,
    normal_quantile,
    poisson_quantile,
)


def test_normal_quantile_median_equals_mean():
    assert normal_quantile(mean=10.0, std=2.0, quantile=0.5) == pytest.approx(10.0)


def test_normal_quantile_increases_with_quantile():
    low = normal_quantile(mean=10.0, std=2.0, quantile=0.1)
    high = normal_quantile(mean=10.0, std=2.0, quantile=0.9)
    assert low < 10.0 < high


def test_poisson_quantile_at_high_quantile_exceeds_mean():
    assert poisson_quantile(mean=5.0, quantile=0.95) > 5.0


def test_poisson_quantile_returns_integer_valued_float():
    value = poisson_quantile(mean=5.0, quantile=0.5)
    assert value == pytest.approx(round(value))


def test_empirical_bootstrap_quantile_is_deterministic_given_seed():
    demand = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    a = empirical_bootstrap_quantile(
        demand, window_days=7, quantile=0.9, n_simulations=500, random_seed=42
    )
    b = empirical_bootstrap_quantile(
        demand, window_days=7, quantile=0.9, n_simulations=500, random_seed=42
    )
    assert a == b


def test_empirical_bootstrap_quantile_differs_with_different_seed():
    # Non-integer, varied values make bootstrap-sum quantiles effectively
    # continuous, so two different seeds essentially never collide exactly
    # (unlike a small set of round integers, where they occasionally do).
    demand = np.array([1.3, 2.7, 4.1, 3.6, 2.9, 5.4, 3.2, 4.8])
    a = empirical_bootstrap_quantile(
        demand, window_days=7, quantile=0.9, n_simulations=500, random_seed=1
    )
    b = empirical_bootstrap_quantile(
        demand, window_days=7, quantile=0.9, n_simulations=500, random_seed=2
    )
    assert a != b


def test_empirical_bootstrap_quantile_scales_with_window():
    demand = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    short = empirical_bootstrap_quantile(
        demand, window_days=1, quantile=0.5, n_simulations=2000, random_seed=7
    )
    long = empirical_bootstrap_quantile(
        demand, window_days=7, quantile=0.5, n_simulations=2000, random_seed=7
    )
    # Summing over more days roughly multiplies the central quantile by the window size.
    assert long == pytest.approx(short * 7, rel=0.2)


def test_empirical_bootstrap_quantile_rejects_empty_array():
    with pytest.raises(ValueError, match="must not be empty"):
        empirical_bootstrap_quantile(
            np.array([]), window_days=7, quantile=0.9, n_simulations=100, random_seed=42
        )
