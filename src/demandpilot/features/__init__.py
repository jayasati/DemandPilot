"""Feature engineering: config-driven SQL generation and versioned snapshots.

``configs/features.yaml`` is the single source of truth for the feature set
(ADR-010) — ``FeatureSqlGenerator`` renders the leakage-safe rolling-feature
SQL from it. ``FeatureSnapshotBuilder`` then materializes the joined feature
store into a versioned ``feature_store_v{N}`` table with a lineage manifest
(ADR-011), so every model trains on data that can be reproduced exactly.
"""

from demandpilot.features.generator import FeatureSqlGenerator
from demandpilot.features.snapshots import (
    FeatureSnapshotBuilder,
    SnapshotInfo,
    latest_snapshot_table,
)

__all__ = [
    "FeatureSnapshotBuilder",
    "FeatureSqlGenerator",
    "SnapshotInfo",
    "latest_snapshot_table",
]
