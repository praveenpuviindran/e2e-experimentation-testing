from pathlib import Path


def test_expected_directories_exist() -> None:
    """All required project directories must exist for the pipeline and dashboard to run.

    Verifies the canonical repo layout (src/, sql/, data/, reports/, docs/, tests/)
    so that CI catches accidental directory removals or renames early.
    """
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
