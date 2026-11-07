import pytest

from tools.research.evaluate_rtc_polarization_sensitivity import (
    PolarizationSensitivityError,
    compare_spatial_support,
)


def _record(polarization, changes):
    values = ([-2.0, -1.0, 1.0] if polarization == "VV" else [-1.0, 0.0, 2.0])
    return {
        "record_type": "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC",
        "status": "DIAGNOSTIC_SPATIAL_ASSOCIATION",
        "sources": {
            "sar_polarization": polarization,
            "sar_pair_status": "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON",
            "sar_provider_qa": {"status": "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"},
            "sar_scene_ids": ["S1_BEFORE", "S1_AFTER"],
            "optical_granule_ids": ["OPT_BEFORE", "OPT_AFTER"],
            "optical_context_record_sha256": "optical-record-hash",
            "sar_grid_crs": "EPSG:32622",
            "optical_wtr_source_sha256": ["wtr-before", "wtr-after"],
            "sar_pair_record": f"{polarization}.json",
            "sar_pair_record_sha256": f"{polarization}-hash",
        },
        "per_sar_cell": [
            {
                "sar_row": i,
                "sar_column": 0,
                "common_valid_wtr_area_fraction": 0.9,
                "water_fraction_change_after_minus_before": changes[i],
                "sar_measurement_valid": True,
                "sar_log_ratio_db": values[i],
            }
            for i in range(3)
        ],
    }


def test_polarization_comparison_uses_same_cells_and_preserves_diagnostic_status():
    vv = _record("VV", [-0.2, 0.0, 0.4])
    vh = _record("VH", [-0.2, 0.0, 0.4])

    result = compare_spatial_support(vv, vh)

    assert result["status"] == "DIAGNOSTIC_SENSITIVITY_ONLY"
    assert result["summary"]["common_cells"] == 3
    assert result["summary"]["vv_pearson_r_water_change_vs_log_ratio"] == pytest.approx(1.0)
    assert result["summary"]["vh_pearson_r_water_change_vs_log_ratio"] == pytest.approx(1.0)
    assert "not independent validation" in result["scope"]


def test_polarization_comparison_rejects_different_optical_support():
    vv = _record("VV", [-0.2, 0.0, 0.4])
    vh = _record("VH", [-0.2, 0.0, 0.4])
    vh["per_sar_cell"][0]["common_valid_wtr_area_fraction"] = 0.1

    with pytest.raises(PolarizationSensitivityError, match="optical support differs"):
        compare_spatial_support(vv, vh)


def test_polarization_comparison_rejects_cleared_or_mismatched_sources():
    vv = _record("VV", [-0.2, 0.0, 0.4])
    vh = _record("VH", [-0.2, 0.0, 0.4])
    vh["sources"]["sar_scene_ids"] = ["OTHER_BEFORE", "OTHER_AFTER"]

    with pytest.raises(PolarizationSensitivityError, match="sar_scene_ids differ"):
        compare_spatial_support(vv, vh)

    vv = _record("VV", [-0.2, 0.0, 0.4])
    vv["sources"]["sar_provider_qa"]["status"] = "PASS"
    with pytest.raises(PolarizationSensitivityError, match="provider QA state"):
        compare_spatial_support(vv, _record("VH", [-0.2, 0.0, 0.4]))
