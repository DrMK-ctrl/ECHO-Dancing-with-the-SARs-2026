import json
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
import pytest

from tools.research.screen_smap_l4_context import (
    _select_granule,
    summarize_subset,
)


def _granule(granule_id, concept_id):
    return {
        "meta": {"concept-id": concept_id},
        "umm": {
            "GranuleUR": granule_id,
            "TemporalExtent": {
                "RangeDateTime": {
                    "BeginningDateTime": "2024-05-11T07:30:00.000Z",
                    "EndingDateTime": "2024-05-11T10:30:00.000Z",
                }
            },
            "CollectionReference": {"ShortName": "SPL4SMAU", "Version": "008"},
        },
    }


def test_select_granule_chooses_nearest_analysis_within_declared_offset():
    selected = _granule("SMAP_L4_SM_aup_20240511T090000_Vv8012_001.h5_I5bjLDJh", "G1")
    earlier = _granule("SMAP_L4_SM_aup_20240511T060000_Vv8012_001.h5_I5bjLDJh", "G0")

    result = _select_granule(
        {"granules": [earlier, selected]},
        target_time=datetime.fromisoformat("2024-05-11T08:49:47+00:00"),
        max_offset_minutes=90,
    )

    assert result["granule_id"] == selected["umm"]["GranuleUR"]
    assert result["concept_id"] == "G1"
    assert result["offset_minutes"] == pytest.approx(10.2166667)
    with pytest.raises(ValueError, match="nearest SMAP L4 analysis"):
        _select_granule(
            {"granules": [earlier]},
            target_time=datetime.fromisoformat("2024-05-11T08:49:47+00:00"),
            max_offset_minutes=30,
        )


def test_summarize_subset_preserves_native_values_fill_counts_and_history(tmp_path):
    granule_id = "SMAP_L4_SM_aup_20240511T090000_Vv8012_001.h5_I5bjLDJh"
    path = tmp_path / "bounded.nc4"
    values = {
        "Analysis_Data/sm_surface_analysis": (np.array([[0.3, -9999.0]]), "m3 m-3"),
        "Analysis_Data/sm_surface_analysis_ensstd": (np.array([[0.02, 0.03]]), "m3 m-3"),
        "Observations_Data/tb_h_obs_assim": (np.array([[-9999.0, -9999.0]]), "K"),
        "Observations_Data/tb_v_obs_assim": (np.array([[-9999.0, -9999.0]]), "K"),
        "Observations_Data/tb_h_obs_time_sec": (np.array([[-9999.0, -9999.0]]), "s"),
        "Observations_Data/tb_v_obs_time_sec": (np.array([[-9999.0, -9999.0]]), "s"),
    }
    with h5py.File(path, "w") as target:
        target.create_dataset("cell_lat", data=np.array([[-30.0, -30.0]]))
        target.create_dataset("cell_lon", data=np.array([[-51.2, -51.1]]))
        for name, (array, units) in values.items():
            dataset = target.create_dataset(name, data=array)
            dataset.attrs["_FillValue"] = -9999.0
            dataset.attrs["units"] = units
        target.attrs["history_json"] = json.dumps([
            {"parameters": [{"request_url": f"https://harmony.test/{granule_id}"}]}
        ])

    result = summarize_subset(path, granule_id, project_root=tmp_path)

    assert result["asset"]["relative_path"] == "bounded.nc4"
    assert result["variables"]["Analysis_Data/sm_surface_analysis"]["valid_cell_count"] == 1
    assert result["variables"]["Analysis_Data/sm_surface_analysis"]["values"] == [[0.3, -9999.0]]
    assert result["variables"]["Observations_Data/tb_v_obs_assim"]["valid_cell_count"] == 0
    assert result["grid"]["shape"] == [1, 2]
    assert result["harmony_history"][0]["parameters"][0]["request_url"].endswith(granule_id)


def test_summarize_subset_rejects_wrong_granule_history(tmp_path):
    path = tmp_path / "bounded.nc4"
    with h5py.File(path, "w") as target:
        target.create_dataset("cell_lat", data=np.array([[0.0]]))
        target.create_dataset("cell_lon", data=np.array([[0.0]]))
        for name in (
            "Analysis_Data/sm_surface_analysis",
            "Analysis_Data/sm_surface_analysis_ensstd",
            "Observations_Data/tb_h_obs_assim",
            "Observations_Data/tb_v_obs_assim",
            "Observations_Data/tb_h_obs_time_sec",
            "Observations_Data/tb_v_obs_time_sec",
        ):
            target.create_dataset(name, data=np.array([[0.1]]))
        target.attrs["history_json"] = json.dumps([{"parameters": [{"request_url": "different-source"}]}])

    with pytest.raises(ValueError, match="different source granule"):
        summarize_subset(path, "expected-source", project_root=tmp_path)
