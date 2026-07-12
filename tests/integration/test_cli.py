"""End-to-end CLI tests: init-db -> ingest-m5 -> validate on a throwaway root."""

import pytest

from demandpilot.cli import main

pytestmark = pytest.mark.integration


def test_full_pipeline(tmp_project, m5_fixture_dir, reset_logging):
    root = str(tmp_project)
    assert main(["--root", root, "init-db"]) == 0
    assert main(["--root", root, "ingest-m5", "--raw-dir", str(m5_fixture_dir)]) == 0
    assert main(["--root", root, "build-features"]) == 0
    assert main(["--root", root, "validate"]) == 0
    assert (tmp_project / "data" / "demandpilot.duckdb").is_file()
    assert (tmp_project / "logs" / "demandpilot.log").is_file()


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
