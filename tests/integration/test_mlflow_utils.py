"""Tests for MLflow run lookup against a real (temporary) tracking backend."""

import mlflow
import pytest

from demandpilot.mlflow_utils import latest_run

pytestmark = pytest.mark.integration


def test_latest_run_returns_none_for_missing_experiment(tmp_path):
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    assert latest_run(uri, "does-not-exist") is None


def test_latest_run_returns_most_recent_run(tmp_path):
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("test-latest-run")
    with mlflow.start_run():
        mlflow.log_param("snapshot_table", "feature_store_v1")
        mlflow.log_metric("wape", 0.3)
    with mlflow.start_run() as second:
        mlflow.log_param("snapshot_table", "feature_store_v2")
        mlflow.log_metric("wape", 0.2)
        expected_run_id = second.info.run_id

    result = latest_run(uri, "test-latest-run")
    assert result is not None
    assert result.run_id == expected_run_id
    assert result.metrics["wape"] == pytest.approx(0.2)
    assert result.params["snapshot_table"] == "feature_store_v2"
