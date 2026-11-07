import numpy as np
import pytest

from echo.opera_rtc import (
    analyze_opera_rtc_s1_pair,
    common_opera_rtc_s1_clear_mask,
    decode_opera_rtc_s1_mask,
)


def test_decode_opera_rtc_s1_mask_keeps_documented_categories_distinct():
    result = decode_opera_rtc_s1_mask(
        np.array([[0, 1, 2, 3, 255]], dtype=np.uint8)
    )

    np.testing.assert_array_equal(result.clear, [[True, False, False, False, False]])
    np.testing.assert_array_equal(
        result.shadow_affected, [[False, True, False, True, False]]
    )
    np.testing.assert_array_equal(
        result.layover_affected, [[False, False, True, True, False]]
    )
    np.testing.assert_array_equal(result.invalid, [[False, False, False, False, True]])


def test_common_mask_uses_only_same_aoi_pixels_clear_on_both_dates():
    before = np.array([[0, 0, 1, 2, 3, 255]], dtype=np.uint8)
    after = np.array([[0, 1, 0, 2, 0, 0]], dtype=np.uint8)
    selected = np.array([[True, True, True, True, True, False]])

    result = common_opera_rtc_s1_clear_mask(before, after, selected)

    np.testing.assert_array_equal(
        result.common_clear, [[True, False, False, False, False, False]]
    )
    assert result.aoi_pixel_count == 5
    assert result.before_clear_count == 2
    assert result.after_clear_count == 3
    assert result.before_shadow_affected_count == 2
    assert result.after_shadow_affected_count == 1
    assert result.before_layover_affected_count == 2
    assert result.after_layover_affected_count == 1
    assert result.before_invalid_count == 0
    assert result.after_invalid_count == 0


@pytest.mark.parametrize(
    "mask, message",
    [
        (np.array([0, 1], dtype=np.uint8), "two-dimensional"),
        (np.array([[0, 4]], dtype=np.uint8), "undocumented codes"),
        (np.array([[0.0, 1.0]], dtype=np.float32), "integer array"),
    ],
)
def test_decode_rejects_unrecognized_mask_shapes_types_and_codes(mask, message):
    with pytest.raises(ValueError, match=message):
        decode_opera_rtc_s1_mask(mask)


def test_common_mask_rejects_grid_shape_or_aoi_shape_mismatch():
    with pytest.raises(ValueError, match="identical shapes"):
        common_opera_rtc_s1_clear_mask(
            np.zeros((2, 2), dtype=np.uint8), np.zeros((2, 3), dtype=np.uint8)
        )
    with pytest.raises(ValueError, match="AOI selection mask"):
        common_opera_rtc_s1_clear_mask(
            np.zeros((2, 2), dtype=np.uint8),
            np.zeros((2, 2), dtype=np.uint8),
            np.ones((2, 3), dtype=bool),
        )


def test_pair_measurement_requires_same_grid_and_uses_clear_common_pixels():
    before = np.array([[1.0, 2.0], [4.0, 1.0]], dtype=np.float32)
    after = np.array([[2.0, 2.0], [2.0, np.nan]], dtype=np.float32)
    before_mask = np.array([[0, 0], [1, 0]], dtype=np.uint8)
    after_mask = np.array([[0, 1], [0, 0]], dtype=np.uint8)
    transform = (30.0, 0.0, 500000.0, 0.0, -30.0, 6700000.0)

    result = analyze_opera_rtc_s1_pair(
        before,
        after,
        before_mask,
        after_mask,
        before_crs="EPSG:32722",
        after_crs="EPSG:32722",
        before_transform=transform,
        after_transform=transform,
    )

    assert result.change.valid_count == 1
    assert result.change.values_db[0, 0] == pytest.approx(10 * np.log10(2))
    assert np.isnan(result.change.values_db[0, 1])
    assert not result.change.valid_mask[1, 0]
    assert not result.change.valid_mask[1, 1]


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"after_crs": "EPSG:32723"}, "CRS values must match"),
        ({"after_transform": (30, 0, 500001, 0, -30, 6700000)}, "affine transforms must match"),
    ],
)
def test_pair_measurement_fails_closed_when_grid_differs(changes, message):
    options = {
        "before_crs": "EPSG:32722",
        "after_crs": "EPSG:32722",
        "before_transform": (30, 0, 500000, 0, -30, 6700000),
        "after_transform": (30, 0, 500000, 0, -30, 6700000),
    }
    options.update(changes)
    with pytest.raises(ValueError, match=message):
        analyze_opera_rtc_s1_pair(
            np.ones((2, 2)),
            np.ones((2, 2)),
            np.zeros((2, 2), dtype=np.uint8),
            np.zeros((2, 2), dtype=np.uint8),
            **options,
        )
