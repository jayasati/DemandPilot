"""Tests for MLflow tracking-URI resolution (pure, no I/O)."""

import pytest

from demandpilot.mlflow_utils import resolve_mlflow_tracking_uri


@pytest.mark.parametrize("prefix", ["sqlite:///", "file:"])
def test_resolve_relative_uri_against_root(tmp_path, prefix):
    result = resolve_mlflow_tracking_uri(f"{prefix}mlruns/mlflow.db", tmp_path)
    assert result.startswith(prefix)
    assert str(tmp_path.resolve().as_posix()) in result
    assert result.endswith("mlruns/mlflow.db")


def test_absolute_sqlite_uri_passes_through(tmp_path):
    absolute = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    assert resolve_mlflow_tracking_uri(absolute, tmp_path) == absolute


def test_non_file_scheme_passes_through(tmp_path):
    uri = "http://mlflow.internal:5000"
    assert resolve_mlflow_tracking_uri(uri, tmp_path) == uri
