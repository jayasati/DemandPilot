"""Unit tests for the reporting data-gathering helpers (pure parsing)."""

from demandpilot.reporting.data import _parse_quantile_metrics


def test_parses_matched_pinball_and_coverage_pairs():
    metrics = {
        "pinball_q0_1": 1.5,
        "coverage_q0_1": 0.11,
        "pinball_q0_5": 0.8,
        "coverage_q0_5": 0.49,
        "wape": 0.2,  # unrelated metric must be ignored
    }
    result = _parse_quantile_metrics(metrics)
    assert [qm.quantile for qm in result] == [0.1, 0.5]
    by_quantile = {qm.quantile: qm for qm in result}
    assert by_quantile[0.1].pinball == 1.5
    assert by_quantile[0.1].coverage == 0.11
    assert by_quantile[0.5].pinball == 0.8
    assert by_quantile[0.5].coverage == 0.49


def test_handles_missing_coverage_for_a_quantile():
    metrics = {"pinball_q0_9": 2.0}
    result = _parse_quantile_metrics(metrics)
    assert len(result) == 1
    assert result[0].quantile == 0.9
    assert result[0].pinball == 2.0
    import math

    assert math.isnan(result[0].coverage)


def test_empty_metrics_yields_empty_tuple():
    assert _parse_quantile_metrics({}) == ()


def test_results_are_sorted_by_quantile():
    metrics = {"pinball_q0_9": 1.0, "pinball_q0_1": 1.0, "pinball_q0_5": 1.0}
    result = _parse_quantile_metrics(metrics)
    assert [qm.quantile for qm in result] == [0.1, 0.5, 0.9]
