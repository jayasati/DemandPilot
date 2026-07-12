"""Quantile demand forecasting: dataset assembly, splitting, training, backtest.

See ADR-008 (target-shift direct multi-horizon formulation), ADR-014
(future-known vs. history-derived feature split), and ADR-015
(horizon-as-feature training with origin sampling).
"""

from demandpilot.forecasting.dataset import HorizonDatasetAssembler, assemble_multi_horizon
from demandpilot.forecasting.pipeline import BacktestReport, ForecastingPipeline, QuantileMetrics
from demandpilot.forecasting.split import DatasetSplit, chronological_split

__all__ = [
    "BacktestReport",
    "DatasetSplit",
    "ForecastingPipeline",
    "HorizonDatasetAssembler",
    "QuantileMetrics",
    "assemble_multi_horizon",
    "chronological_split",
]
