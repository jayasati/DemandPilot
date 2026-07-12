"""Unit tests for snapshot manifest helpers (config hashing, git commit resolution)."""

from demandpilot.config import load_config
from demandpilot.features.snapshots import _current_git_commit, _hash_config


def test_hash_config_is_deterministic(repo_root):
    features = load_config(repo_root).features
    assert _hash_config(features) == _hash_config(features)


def test_hash_config_changes_when_config_changes(repo_root):
    features = load_config(repo_root).features
    changed = features.model_copy(
        update={"lag_features": features.lag_features.model_copy(update={"lags": [1, 2, 3]})}
    )
    assert _hash_config(features) != _hash_config(changed)


def test_current_git_commit_returns_none_outside_a_repo(tmp_path):
    assert _current_git_commit(tmp_path) is None


def test_current_git_commit_returns_a_full_sha_in_this_repo(repo_root):
    commit = _current_git_commit(repo_root)
    assert commit is None or (len(commit) == 40 and all(c in "0123456789abcdef" for c in commit))
