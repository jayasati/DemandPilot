"""Tests for the SQL template renderer."""

import pytest

from demandpilot.exceptions import SqlRenderError
from demandpilot.sqlrender import SqlRenderer


@pytest.fixture
def sql_dir(tmp_path):
    (tmp_path / "query.sql.j2").write_text(
        "SELECT * FROM read_csv('{{ raw_dir }}/x.csv');\n", encoding="utf-8"
    )
    return tmp_path


def test_renders_parameters(sql_dir):
    sql = SqlRenderer(sql_dir).render("query.sql.j2", raw_dir="/data/m5")
    assert sql == "SELECT * FROM read_csv('/data/m5/x.csv');\n"


def test_missing_parameter_fails_loudly(sql_dir):
    with pytest.raises(SqlRenderError, match="raw_dir"):
        SqlRenderer(sql_dir).render("query.sql.j2")


def test_missing_template_raises(sql_dir):
    with pytest.raises(SqlRenderError, match=r"nope\.sql"):
        SqlRenderer(sql_dir).render("nope.sql")


def test_repo_ingest_template_renders(repo_root):
    sql = SqlRenderer(repo_root / "sql").render("ingest_m5.sql.j2", raw_dir="/tmp/m5")
    assert "read_csv('/tmp/m5/calendar.csv'" in sql
    assert "UNPIVOT" in sql
