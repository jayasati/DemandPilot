"""Shared MLflow helpers: tracking-URI resolution and read-only run lookup.

Used by the CLI (before training) and by the reporting layer (read-only,
after training) so both resolve MLflow state the same way.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)


def resolve_mlflow_tracking_uri(tracking_uri: str, root: Path) -> str:
    """Resolve a relative ``sqlite:///``/``file:`` tracking URI against the project root.

    ``configs/app.yaml`` declares ``mlflow.tracking_uri`` as a plain string
    (unlike ``paths.*``, it isn't run through ``PathsConfig.resolve_against``)
    so a relative path would otherwise land relative to the process's current
    working directory rather than ``--root`` — breaking the "no hardcoded
    paths" principle. Absolute URIs and other schemes pass through unchanged.
    """
    for prefix in ("sqlite:///", "file:"):
        if tracking_uri.startswith(prefix):
            raw_path = Path(tracking_uri[len(prefix) :])
            if raw_path.is_absolute():
                return tracking_uri
            return prefix + (root / raw_path).resolve().as_posix()
    return tracking_uri


@dataclass(frozen=True)
class RunSummary:
    """The metrics, params, and identity of one MLflow run."""

    run_id: str
    start_time: datetime
    metrics: dict[str, float]
    params: dict[str, str]


def latest_run(tracking_uri: str, experiment_name: str) -> RunSummary | None:
    """Return the most recent run for ``experiment_name``.

    Args:
        tracking_uri: A fully resolved MLflow tracking URI.
        experiment_name: The experiment to look up.

    Returns:
        The latest run's summary, or ``None`` if the experiment doesn't
        exist or has no runs (e.g. ``demandpilot train`` has never run).
    """
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        return None
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id], order_by=["start_time DESC"], max_results=1
    )
    if not runs:
        return None
    run = runs[0]
    return RunSummary(
        run_id=run.info.run_id,
        start_time=datetime.fromtimestamp(run.info.start_time / 1000, tz=UTC),
        metrics=dict(run.data.metrics),
        params=dict(run.data.params),
    )
