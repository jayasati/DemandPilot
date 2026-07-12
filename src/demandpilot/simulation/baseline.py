"""Classical (non-ML) order-up-to baseline policy.

Dispatches to the pure quantile estimators in ``demandpilot.core.
demand_distribution`` based on ``configs/simulation.yaml``'s
``demand_distribution`` setting — the counterpart the ML quantile forecaster
is compared against in Volume 5's replay (ADR-017).
"""

import math
from typing import Literal

import numpy as np
import numpy.typing as npt

from demandpilot.core.demand_distribution import (
    empirical_bootstrap_quantile,
    normal_quantile,
    poisson_quantile,
)
from demandpilot.exceptions import SimulationError

FloatArray = npt.NDArray[np.float64]

DemandDistribution = Literal["empirical", "normal", "poisson"]


def classical_order_up_to(
    daily_demand: FloatArray,
    lead_time_days: int,
    service_level: float,
    demand_distribution: DemandDistribution,
    n_simulations: int,
    random_seed: int,
) -> float:
    """Order-up-to level for one series under the classical baseline policy.

    Args:
        daily_demand: Historical single-day demand observations for the series.
        lead_time_days: Number of days of demand to cover per order.
        service_level: Target quantile (the critical fractile, in practice).
        demand_distribution: Which distributional assumption to fit.
        n_simulations: Monte Carlo draws (``empirical`` only).
        random_seed: Seed for reproducibility (``empirical`` only).

    Returns:
        The order-up-to quantity.

    Raises:
        SimulationError: If ``daily_demand`` is empty, or
            ``demand_distribution`` is unrecognized (unreachable given
            Pydantic validation, but guarded defensively).
    """
    if daily_demand.size == 0:
        raise SimulationError("daily_demand must not be empty")

    if demand_distribution == "empirical":
        return empirical_bootstrap_quantile(
            daily_demand, lead_time_days, service_level, n_simulations, random_seed
        )

    mean = float(np.mean(daily_demand)) * lead_time_days
    if demand_distribution == "normal":
        std = float(np.std(daily_demand)) * math.sqrt(lead_time_days)
        return normal_quantile(mean, std, service_level)
    if demand_distribution == "poisson":
        return poisson_quantile(mean, service_level)

    raise SimulationError(  # pragma: no cover - unreachable given Literal validation
        f"Unknown demand_distribution: {demand_distribution!r}"
    )
