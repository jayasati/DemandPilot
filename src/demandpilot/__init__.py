"""DemandPilot — decision-intelligence platform for retail demand forecasting.

Layers (dependencies point inward only — see docs/ARCHITECTURE.md):

- ``core``: pure domain logic (math, metrics). No I/O, no framework imports.
- ``config``: typed, validated configuration models and loading.
- ``data``: DuckDB access, ingestion, and data validation.
- ``cli``: command-line entry point.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("demandpilot")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"
