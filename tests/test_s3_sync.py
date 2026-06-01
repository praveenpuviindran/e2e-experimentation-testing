from pathlib import Path

from src.pipeline.s3_sync import _build_s3_key, _normalize_prefix, _relative_from_key


def test_normalize_prefix() -> None:
    """S3 key prefix normalisation should always produce a trailing slash (or empty string).

    Ensures leading slashes are stripped and trailing slashes are added consistently
    so S3 key construction is deterministic regardless of caller formatting.
    """
    assert _normalize_prefix("mindlift/raw") == "mindlift/raw/"
    assert _normalize_prefix("/mindlift/raw/") == "mindlift/raw/"
    assert _normalize_prefix("") == ""


def test_build_and_reverse_key() -> None:
    """S3 key construction and reversal should be inverse operations.

    Given a local file path relative to a local_dir, _build_s3_key should produce
    a key like <prefix>/<relative_path>. _relative_from_key should reverse this
    to recover the original relative path.
    """
    local_dir = Path("data/raw")
    local_file = Path("data/raw/events/2025-01-01/fact_events.csv")

    key = _build_s3_key(prefix="mindlift/raw", local_file=local_file, local_dir=local_dir)
    assert key == "mindlift/raw/events/2025-01-01/fact_events.csv"

    rel = _relative_from_key(prefix="mindlift/raw", key=key)
    assert rel.as_posix() == "events/2025-01-01/fact_events.csv"
