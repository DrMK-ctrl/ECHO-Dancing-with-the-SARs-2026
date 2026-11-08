from echo.modis_ga import (
    decode_mod09ga_band_qa,
    decode_mod09ga_state_qa,
    mod09ga_vegetation_sample_accepted,
    normalized_difference_vegetation_index,
)


def test_decode_mod09ga_daily_band_and_state_flags():
    assert decode_mod09ga_band_qa(1073741824) == {
        "modland_quality": 0,
        "band1_quality": 0,
        "band2_quality": 0,
        "atmospheric_correction_performed": 1,
        "adjacency_correction_performed": 0,
    }
    assert decode_mod09ga_state_qa(24)["land_water_class"] == 3
    assert decode_mod09ga_state_qa(24)["cloud_state"] == 0
    assert decode_mod09ga_state_qa(40982)["cloud_shadow"] == 1


def test_mod09ga_vegetation_gate_requires_clear_land_and_good_red_nir():
    # Clear, land-class state; all MODLAND and band quality fields are best.
    clear_land = 1 << 3
    assert mod09ga_vegetation_sample_accepted(1000, 3000, 1 << 30, clear_land)
    assert not mod09ga_vegetation_sample_accepted(1000, 3000, 1 << 30, 24)
    assert not mod09ga_vegetation_sample_accepted(1000, 3000, 1 << 30, 40982)
    assert not mod09ga_vegetation_sample_accepted(-28672, 3000, 1 << 30, clear_land)
    assert not mod09ga_vegetation_sample_accepted(1000, 3000, (1 << 30) | 1, clear_land)


def test_mod09ga_ndvi_uses_scaled_ratio_and_rejects_fill_values():
    assert normalized_difference_vegetation_index(1000, 3000) == 0.5
    assert normalized_difference_vegetation_index(-28672, 3000) is None
    assert normalized_difference_vegetation_index(-100, 100) is None
