from pathlib import Path

from src.pipeline.s3_sync import _build_s3_key, _normalize_prefix, _relative_from_key


def test_normalize_prefix() -> None:
    assert _normalize_prefix("mindlift/raw") == "mindlift/raw/"
    assert _normalize_prefix("/mindlift/raw/") == "mindlift/raw/"
    assert _normalize_prefix("") == ""


def test_build_and_reverse_key() -> None:
    local_dir = Path("data/raw")
    local_file = Path("data/raw/events/2025-01-01/fact_events.csv")

    key = _build_s3_key(prefix="mindlift/raw", local_file=local_file, local_dir=local_dir)
    assert key == "mindlift/raw/events/2025-01-01/fact_events.csv"

    rel = _relative_from_key(prefix="mindlift/raw", key=key)
    assert rel.as_posix() == "events/2025-01-01/fact_events.csv"
