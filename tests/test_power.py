from src.analysis.power import mde_binary_for_sample_size, required_n_per_group_binary


def test_required_n_decreases_for_larger_mde() -> None:
    """Larger minimum detectable effects require fewer samples to achieve the same power.

    A 3pp MDE needs fewer users per group than a 1pp MDE at the same baseline rate,
    because larger effects are inherently easier to detect.
    """
    n_small = required_n_per_group_binary(baseline_rate=0.30, mde_abs=0.01)
    n_large = required_n_per_group_binary(baseline_rate=0.30, mde_abs=0.03)
    assert n_large < n_small


def test_mde_decreases_with_more_samples() -> None:
    """Larger sample sizes allow detection of smaller minimum detectable effects.

    With 10x more users, the MDE should be smaller — the experiment can reliably
    detect finer treatment effects at the same power and significance level.
    """
    mde_low_n = mde_binary_for_sample_size(baseline_rate=0.30, n_control=1000, n_treatment=1000)
    mde_high_n = mde_binary_for_sample_size(baseline_rate=0.30, n_control=10000, n_treatment=10000)
    assert mde_high_n < mde_low_n
