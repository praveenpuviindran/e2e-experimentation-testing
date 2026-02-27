from pathlib import Path


def test_expected_directories_exist() -> None:
    expected_dirs = [
        "src/data_gen",
        "src/pipeline",
        "src/analysis",
        "src/utils",
        "sql/schema",
        "sql/metrics",
        "data/raw",
        "data/processed",
        "reports/figures",
        "reports/tables",
        "tests",
        "docs",
    ]

    for rel_path in expected_dirs:
        assert Path(rel_path).is_dir(), f"Missing directory: {rel_path}"
