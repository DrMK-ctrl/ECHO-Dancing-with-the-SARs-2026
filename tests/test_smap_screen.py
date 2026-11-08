import json
from pathlib import Path

from tools.research.screen_smap_s_candidates import _summarize_subset


PROJECT = Path(__file__).resolve().parents[1]
SCREEN_PATH = PROJECT / "data/research/smap-sentinel-soil-moisture-screen-T163-349925-2026-11-08.json"


def test_retained_exact_aoi_smap_subsets_match_the_screen_record():
    screen = json.loads(SCREEN_PATH.read_text(encoding="utf-8"))

    assert screen["query"]["bbox_west_south_east_north"] == [-51.24, -30.04, -51.23, -30.03]
    assert screen["query"]["same_grid_before_after"] is True
    assert screen["comparison"]["paired_quality_eligible_cells"] == 0
    for observation in screen["observations"]:
        path = PROJECT / observation["asset"]["relative_path"]
        assert _summarize_subset(
            path,
            observation["granule_id"],
            tuple(screen["query"]["bbox_west_south_east_north"]),
        ) == {
            key: value for key, value in observation.items()
            if key in {
                "granule_id",
                "harmony_request_url",
                "history",
                "grid_shape",
                "grid_identity_sha256",
                "quality_eligible_flat_indices",
                "grid_centers_wgs84",
                "aoi_cell_support",
                "soil_moisture",
                "quality_flags",
                "smap_sentinel_time_difference_field",
                "asset",
            }
        }
        assert observation["soil_moisture"]["quality_eligible_cell_count"] == 0
        assert observation["quality_flags"]["retrieval_flag_zero_good_cell_count"] == 0
        assert observation["quality_flags"]["retrieval_quality_compromised_bit_0_cell_count"] == 1
        assert observation["quality_flags"]["disaggregated_brightness_temperature_bad_bit_6_cell_count"] == 1
