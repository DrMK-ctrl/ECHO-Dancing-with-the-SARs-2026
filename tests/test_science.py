"""Synthetic unit tests for numeric GCOV change primitives only."""

import numpy as np
import pytest

from echo.science import gamma0_log_ratio_db, summarize_region


def test_log_ratio_reports_no_change_and_signed_power_ratios():
    before = np.full((1, 3), 4.0, dtype=np.float32)
    after = np.array([[4.0, 8.0, 2.0]], dtype=np.float32)

    result = gamma0_log_ratio_db(before, after, np.ones((1, 3), dtype=bool))

    np.testing.assert_allclose(result.values_db, [[0.0, 3.0103, -3.0103]], atol=1e-4)
    assert result.valid_count == 3
    assert result.candidate_count == 3


def test_invalid_power_and_external_mask_are_excluded():
    before = np.array([[1.0, 0.0, -1.0, np.nan, 2.0]])
    after = np.array([[2.0, 3.0, 4.0, 5.0, np.inf]])
    common = np.array([[True, True, True, True, False]])

    result = gamma0_log_ratio_db(before, after, common)

    assert result.valid_mask.tolist() == [[True, False, False, False, False]]
    assert result.valid_count == 1
    assert np.isnan(result.values_db[0, 1:]).all()


def test_region_summary_is_descriptive_and_empty_region_stays_empty():
    before = np.ones((2, 2), dtype=np.float32)
    after = np.array([[1.0, 2.0], [4.0, 8.0]], dtype=np.float32)
    field = gamma0_log_ratio_db(before, after, np.ones((2, 2), dtype=bool))

    summary = summarize_region(field, np.array([[True, True], [False, False]]))
    assert summary.sample_count == 2
    assert summary.median_db == pytest.approx(1.50515, abs=1e-4)
    assert summary.lower_quartile_db == pytest.approx(0.752575, abs=1e-4)
    assert summary.upper_quartile_db == pytest.approx(2.257725, abs=1e-4)

    empty = summarize_region(field, np.zeros((2, 2), dtype=bool))
    assert empty.sample_count == 0
    assert empty.median_db is None
    assert empty.lower_quartile_db is None
    assert empty.upper_quartile_db is None


@pytest.mark.parametrize(
    "before, after, mask",
    [
        (np.ones(4), np.ones(4), np.ones(4, dtype=bool)),
        (np.ones((2, 2)), np.ones((2, 1)), np.ones((2, 2), dtype=bool)),
        (np.ones((2, 2)), np.ones((2, 2)), np.ones((2, 1), dtype=bool)),
    ],
)
def test_shape_and_dimension_mismatches_fail_closed(before, after, mask):
    with pytest.raises(ValueError):
        gamma0_log_ratio_db(before, after, mask)


def test_region_shape_mismatch_fails_closed():
    field = gamma0_log_ratio_db(
        np.ones((2, 2)), np.ones((2, 2)), np.ones((2, 2), dtype=bool)
    )
    with pytest.raises(ValueError, match="region mask"):
        summarize_region(field, np.ones((2, 1), dtype=bool))
