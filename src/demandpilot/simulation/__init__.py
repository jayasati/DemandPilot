"""Historical policy-replay simulation (ADR-017).

Compares the ML quantile-forecast policy (reusing Volume 3/4's assembly and
training machinery) against a classical, non-ML baseline (order-up-to level
from a fitted demand distribution) on real historical outcomes — "what would
each policy have cost us." Both are instances of the same newsvendor decision
framework (`configs/simulation.yaml`'s `policy: newsvendor`); they differ only
in how the demand distribution is estimated.
"""

from demandpilot.simulation.baseline import classical_order_up_to
from demandpilot.simulation.replay import (
    SIMULATION_RESULTS_TABLE,
    PolicyComparison,
    PolicyDecision,
    PolicyMetrics,
    SimulationEngine,
    persist_simulation_results,
)

__all__ = [
    "SIMULATION_RESULTS_TABLE",
    "PolicyComparison",
    "PolicyDecision",
    "PolicyMetrics",
    "SimulationEngine",
    "classical_order_up_to",
    "persist_simulation_results",
]
