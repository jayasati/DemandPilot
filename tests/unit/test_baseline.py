"""Tests for the classical baseline policy dispatch."""

import numpy as np
import pytest

from demandpilot.exceptions import SimulationError
from demandpilot.simulation.baseline import classical_order_up_to


def _demand() -> np.ndarray:
    return np.array([2.0, 3.0, 4.0, 3.0, 2.0, 5.0, 4.0], dtype=np.float64)


def test_empirical_dispatch_is_deterministic_given_seed():
    a = classical_order_up_to(_demand(), 7, 0.9, "empirical", 500, 42)
    b = classical_order_up_to(_demand(), 7, 0.9, "empirical", 500, 42)
    assert a == b


def test_normal_dispatch_scales_mean_by_lead_time():
    daily_mean = float(np.mean(_demand()))
    result = classical_order_up_to(_demand(), 7, 0.5, "normal", 100, 42)
    assert result == pytest.approx(daily_mean * 7, rel=1e-6)


def test_poisson_dispatch_scales_mean_by_lead_time():
    daily_mean = float(np.mean(_demand()))
    result = classical_order_up_to(_demand(), 7, 0.5, "poisson", 100, 42)
    assert result == pytest.approx(round(daily_mean * 7), abs=1.0)


def test_higher_service_level_never_orders_less():
    low = classical_order_up_to(_demand(), 7, 0.5, "normal", 100, 42)
    high = classical_order_up_to(_demand(), 7, 0.95, "normal", 100, 42)
    assert high >= low


def test_rejects_empty_history():
    with pytest.raises(SimulationError, match="must not be empty"):
        classical_order_up_to(np.array([]), 7, 0.9, "empirical", 500, 42)
