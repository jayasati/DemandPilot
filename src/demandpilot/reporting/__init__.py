"""Executive HTML report generation (ADR-018).

Presentation layer: renders what Volumes 1-5 already computed and
persisted — no new decisions are made here (ARCHITECTURE.md's "presentation
contains zero business logic" rule).
"""

from demandpilot.reporting.builder import ReportBuilder
from demandpilot.reporting.data import ReportData, gather_report_data

__all__ = ["ReportBuilder", "ReportData", "gather_report_data"]
