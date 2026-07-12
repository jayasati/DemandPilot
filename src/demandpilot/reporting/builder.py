"""Renders the executive HTML report from gathered data.

Presentation layer (ARCHITECTURE.md): makes no new decisions, only formats
what ``demandpilot.reporting.data`` already gathered. Templates ship as
package data alongside this module (not a runtime-configurable path) — see
the ``.gitignore`` note that report templates are code, not generated output.
"""

import logging
from pathlib import Path

import duckdb
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from demandpilot.config.models import CostsConfig, ForecastConfig
from demandpilot.exceptions import ReportingError
from demandpilot.reporting.data import gather_report_data

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "executive_report.html.j2"


def _format_number(value: float, decimals: int = 1) -> str:
    """Thousands-separated number, e.g. ``1,234.5``."""
    return f"{value:,.{decimals}f}"


def _format_money(value: float, currency: str) -> str:
    """Thousands-separated currency amount, e.g. ``USD 1,234.56``."""
    return f"{currency} {value:,.2f}"


def _format_pct(value: float) -> str:
    """Ratio as a percentage, e.g. ``58.4%``."""
    return f"{value:.1%}"


class ReportBuilder:
    """Builds the executive HTML report."""

    def __init__(self, sql_dir: Path) -> None:
        """Create a builder.

        Args:
            sql_dir: Directory containing SQL files (schema SQL and the
                report's own summary queries).
        """
        self._sql_dir = sql_dir
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            undefined=StrictUndefined,
            autoescape=True,  # HTML output, unlike SqlRenderer's SQL templates
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._env.filters["number"] = _format_number
        self._env.filters["money"] = _format_money
        self._env.filters["pct"] = _format_pct

    def build(
        self,
        connection: duckdb.DuckDBPyConnection,
        forecast_config: ForecastConfig,
        costs_config: CostsConfig,
        tracking_uri: str,
        output_path: Path,
        snapshot_table: str | None = None,
    ) -> Path:
        """Gather data and render the report to ``output_path``.

        Args:
            connection: Open (read-only is sufficient) DuckDB connection.
            forecast_config: Supplies the MLflow experiment name.
            costs_config: Supplies the cost-assumptions section.
            tracking_uri: A fully resolved MLflow tracking URI.
            output_path: Where to write the HTML file.
            snapshot_table: Feature snapshot to report lineage for; defaults
                to the most recently built one.

        Returns:
            ``output_path``.

        Raises:
            ReportingError: If the template fails to render or the file
                cannot be written.
        """
        data = gather_report_data(
            connection, self._sql_dir, forecast_config, costs_config, tracking_uri, snapshot_table
        )
        try:
            html = self._env.get_template(_TEMPLATE_NAME).render(report=data)
        except TemplateError as exc:
            raise ReportingError(f"Failed to render {_TEMPLATE_NAME}: {exc}") from exc

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")
        except OSError as exc:
            raise ReportingError(f"Failed to write report to {output_path}: {exc}") from exc

        logger.info("Wrote executive report to %s", output_path)
        return output_path
