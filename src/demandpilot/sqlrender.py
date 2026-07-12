"""Jinja2-based rendering of SQL templates from the ``sql/`` directory.

All SQL lives in ``sql/`` (plain ``.sql`` for static statements, ``.sql.j2``
for parameterized templates) — never as ad-hoc strings inside Python. Templates
use ``StrictUndefined`` so a missing parameter fails loudly instead of
rendering broken SQL.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from demandpilot.exceptions import SqlRenderError


class SqlRenderer:
    """Renders SQL templates from a directory of ``.sql`` / ``.sql.j2`` files."""

    def __init__(self, sql_dir: Path) -> None:
        """Create a renderer over ``sql_dir``.

        Args:
            sql_dir: Directory containing SQL files and Jinja2 templates.
        """
        self._sql_dir = sql_dir
        self._env = Environment(
            loader=FileSystemLoader(str(sql_dir)),
            undefined=StrictUndefined,
            autoescape=False,  # SQL, not HTML; parameters are paths/identifiers, not user input
            keep_trailing_newline=True,
        )

    def render(self, template_name: str, **params: object) -> str:
        """Render a SQL template with the given parameters.

        Args:
            template_name: File name relative to the SQL directory.
            **params: Template variables. Callers must pass trusted values
                (paths, identifiers) — this is not an escaping mechanism.

        Returns:
            The rendered SQL text.

        Raises:
            SqlRenderError: If the template is missing or rendering fails.
        """
        try:
            return self._env.get_template(template_name).render(**params)
        except TemplateError as exc:
            raise SqlRenderError(
                f"Failed to render SQL template '{template_name}' from {self._sql_dir}: {exc}"
            ) from exc
