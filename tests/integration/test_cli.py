"""End-to-end CLI tests: init-db -> ingest-m5 -> build-features -> train ->
recommend -> simulate -> validate."""

import pytest

from demandpilot.cli import main

pytestmark = pytest.mark.integration

_SMALL_FORECAST_YAML = """
target_column: units_sold
date_column: date
id_columns: [store_id, sku_id]
horizon_days: 3
frequency: D
strategy: direct
quantiles: [0.1, 0.5, 0.9]
metrics: [pinball, coverage, wape, bias, rmse]
train:
  test_size_days: 3
  validation_size_days: 3
  cv_folds: 1
  origin_stride_days: 1
model:
  type: lightgbm
  objective: quantile
  params:
    num_leaves: 7
    learning_rate: 0.1
    n_estimators: 15
    max_depth: -1
    min_child_samples: 5
    subsample: 1.0
    colsample_bytree: 1.0
    random_state: 42
  early_stopping_rounds: 5
mlflow:
  experiment_name: test-cli-forecast
  register_model: false
  model_name: test-cli-model
"""


def test_full_pipeline(tmp_project, m5_fixture_dir, reset_logging):
    root = str(tmp_project)
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "validate"]) == 0
    assert (tmp_project / "data" / "demandpilot.duckdb").is_file()
    assert (tmp_project / "logs" / "demandpilot.log").is_file()


def test_train_fails_cleanly_when_fixture_is_too_small_for_default_config(
    tmp_project, m5_fixture_dir, reset_logging
):
    """The tiny CI fixture is deliberately smaller than production; it doesn't
    satisfy forecast.yaml's real-world split sizes, and `train` must fail with
    a clear, actionable message rather than an obscure crash."""
    root = str(tmp_project)
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "train"]) == 1


def test_train_succeeds_with_a_split_sized_for_the_fixture(
    tmp_project, m5_fixture_dir, reset_logging
):
    root = str(tmp_project)
    (tmp_project / "configs" / "forecast.yaml").write_text(_SMALL_FORECAST_YAML, encoding="utf-8")
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "train"]) == 0
    # mlflow.tracking_uri ("sqlite:///mlruns/mlflow.db") must resolve against
    # --root, not cwd.
    assert (tmp_project / "mlruns" / "mlflow.db").is_file()


def test_recommend_succeeds_with_a_split_sized_for_the_fixture(
    tmp_project, m5_fixture_dir, reset_logging
):
    root = str(tmp_project)
    (tmp_project / "configs" / "forecast.yaml").write_text(_SMALL_FORECAST_YAML, encoding="utf-8")
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "recommend", "--lead-time-days", "3"]) == 0


def test_recommend_fails_cleanly_when_lead_time_exceeds_data_range(
    tmp_project, m5_fixture_dir, reset_logging
):
    root = str(tmp_project)
    (tmp_project / "configs" / "forecast.yaml").write_text(_SMALL_FORECAST_YAML, encoding="utf-8")
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "recommend", "--lead-time-days", "1000"]) == 1


def test_simulate_succeeds_with_a_split_sized_for_the_fixture(
    tmp_project, m5_fixture_dir, reset_logging
):
    root = str(tmp_project)
    (tmp_project / "configs" / "forecast.yaml").write_text(_SMALL_FORECAST_YAML, encoding="utf-8")
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "simulate"]) == 0


def test_simulate_fails_cleanly_when_lead_time_exceeds_data_range(
    tmp_project, m5_fixture_dir, reset_logging
):
    root = str(tmp_project)
    (tmp_project / "configs" / "forecast.yaml").write_text(_SMALL_FORECAST_YAML, encoding="utf-8")
    (tmp_project / "configs" / "simulation.yaml").write_text(
        "policy: newsvendor\nservice_level: 0.9\nlead_time_days: 1000\n"
        "review_period_days: 1\ndemand_distribution: empirical\n"
        "n_simulations: 200\nrandom_seed: 42\n",
        encoding="utf-8",
    )
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "simulate"]) == 1


def test_ingest_with_missing_raw_dir_fails(tmp_project, reset_logging):
    root = str(tmp_project)
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5"]) == 1  # default m5 raw dir is empty


def test_broken_config_fails_cleanly(tmp_project, capsys):
    (tmp_project / "configs" / "costs.yaml").write_text(
        "currency: USD\nunit_cost_ratio: 0.5\nsalvage_ratio: 0.9\n"
        "holding_cost_ratio: 0.0\nstockout_penalty_ratio: 0.0\n",
        encoding="utf-8",
    )
    assert main(["--root", str(tmp_project), "init-db"]) == 1
    assert "salvage_ratio" in capsys.readouterr().err
