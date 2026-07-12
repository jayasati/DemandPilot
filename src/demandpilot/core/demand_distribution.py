"""Pure statistical estimators of a demand distribution's quantile from data.

The classical (non-ML) baseline policy Volume 5 compares the quantile
forecaster against (ADR-017): given a distributional assumption and a sample
of historical daily demand, estimate the order-up-to level at a target
quantile. No I/O, no configuration objects (see ARCHITECTURE.md) — callers
pass plain primitives extracted from ``configs/simulation.yaml``.
"""

import numpy as np
import numpy.typing as npt
from scipy import stats

FloatArray = npt.NDArray[np.float64]


def normal_quantile(mean: float, std: float, quantile: float) -> float:
    """Order-up-to level assuming demand is Normal(mean, std).

    Args:
        mean: Mean of the (lead-time) demand distribution.
        std: Standard deviation of the (lead-time) demand distribution.
        quantile: Desired quantile, in (0, 1).

    Returns:
        The quantile of the fitted normal distribution.
    """
    return float(stats.norm.ppf(quantile, loc=mean, scale=std))


def poisson_quantile(mean: float, quantile: float) -> float:
    """Order-up-to level assuming demand is Poisson(mean).

    Args:
        mean: Mean (= variance) of the (lead-time) demand distribution.
        quantile: Desired quantile, in (0, 1).

    Returns:
        The quantile of the fitted Poisson distribution.
    """
    return float(stats.poisson.ppf(quantile, mu=mean))


def empirical_bootstrap_quantile(
    daily_demand: FloatArray,
    window_days: int,
    quantile: float,
    n_simulations: int,
    random_seed: int,
) -> float:
    """Order-up-to level via Monte Carlo bootstrap of lead-time demand.

    Treats ``daily_demand`` as an i.i.d. sample of single-day demand, draws
    ``n_simulations`` bootstrap samples of ``window_days`` days each (with
    replacement), sums each to simulate a lead-time-demand total, and returns
    the empirical ``quantile`` of those simulated totals. This is the
    standard way to estimate a lead-time demand quantile from single-day
    observations without assuming a parametric form.

    Args:
        daily_demand: Historical single-day demand observations.
        window_days: Number of days to sum per simulated draw (the lead time).
        quantile: Desired quantile of the lead-time demand distribution.
        n_simulations: Number of Monte Carlo draws.
        random_seed: Seed for reproducibility.

    Returns:
        The simulated quantile of total lead-time demand.

    Raises:
        ValueError: If ``daily_demand`` is empty.
    """
    if daily_demand.size == 0:
        raise ValueError("daily_demand must not be empty")
    rng = np.random.default_rng(random_seed)
    draws = rng.choice(daily_demand, size=(n_simulations, window_days), replace=True)
    totals = draws.sum(axis=1)
    return float(np.quantile(totals, quantile))
