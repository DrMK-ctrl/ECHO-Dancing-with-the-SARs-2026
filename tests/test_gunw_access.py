from contextlib import contextmanager
from types import SimpleNamespace

import numpy as np
import pytest

import echo.gunw_access as gunw_access
from echo.gunw_access import (
    GunwAccessError,
    decode_gunw_mask,
    read_gunw_window,
)


SCENE_ID = (
    "NISAR_L2_PR_GUNW_032_137_D_068_033_2000_SH_20261009T170432_"
    "20261009T170506_20261021T170432_20261021T170507_P05023_N_F_J_001"
)
COLLECTION = "NISAR_L2_GUNW_PROVISIONAL_V1"
PRODUCT_URL = (
    "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
    f"{COLLECTION}/{SCENE_ID}/{SCENE_ID}.h5"
)
QA_URL = (
    "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
    f"{COLLECTION}/{SCENE_ID}/{SCENE_ID}_QA_SUMMARY.csv"
)
QA_SUMMARY = {
    "observed_provider_status": "FAIL",
    "artifact_uri": QA_URL,
    "artifact_sha256": "a" * 64,
    "retrieved_at_utc": "2026-11-07T00:00:00+00:00",
}


def _feature(*, url=PRODUCT_URL):
    return {
        "properties": {
            "fileID": SCENE_ID,
            "url": url,
            "processingLevel": "GUNW",
            "collectionName": COLLECTION,
            "crid": "P05023",
            "orbit": 6291,
            "pathNumber": 137,
            "frameNumber": 68,
        }
    }


def _mock_product():
    identification = {
        "compositeReleaseId": "P05023",
        "frameNumber": 68,
        "instrumentName": "L-SAR",
        "listOfFrequencies": ["A"],
        "lookDirection": "Left",
        "missionId": "NISAR",
        "orbitPassDirection": "Descending",
        "productSpecificationVersion": "1.5.0",
        "productType": "GUNW",
        "productVersion": "1.0.11",
        "radarBand": "L",
        "referenceAbsoluteOrbitNumber": 6291,
        "referenceHasInputDataException": 0,
        "referenceListOfObservationModes": ["(NOT SPECIFIED)"],
        "referenceZeroDopplerEndTime": "2026-10-09T17:05:06.999342105",
        "referenceZeroDopplerStartTime": "2026-10-09T17:04:32.000000000",
        "secondaryAbsoluteOrbitNumber": 6464,
        "secondaryHasInputDataException": 0,
        "secondaryListOfObservationModes": ["(NOT SPECIFIED)"],
        "secondaryZeroDopplerEndTime": "2026-10-21T17:05:07.999342105",
        "secondaryZeroDopplerStartTime": "2026-10-21T17:04:32.000000000",
        "trackNumber": 137,
    }
    rows, cols = np.indices((8, 9))

    class Dataset:
        def __init__(self, value, attrs=None):
            self.value = value
            self.attrs = attrs or {}
            self.shape = getattr(value, "shape", ())
            self.dtype = getattr(value, "dtype", np.dtype("uint32"))

        def __getitem__(self, key):
            if key == ():
                return self.value
            return self.value[key]

    class Group(dict):
        pass

    id_group = Group(
        {
            name: Dataset(value)
            for name, value in identification.items()
        }
    )
    mask = Dataset(np.full((8, 9), 111, dtype=np.uint32), {"_FillValue": 255})
    grid = Group(
        {
            "mask": mask,
            "xCoordinates": Dataset(np.arange(9, dtype=np.float64) + 500000),
            "yCoordinates": Dataset(np.arange(8, dtype=np.float64) + 4500000),
        }
    )
    data = Group(
        {
            "projection": Dataset(
                np.uint32(32635),
                {"epsg_code": 32635, "grid_mapping_name": b"transverse_mercator"},
            ),
            "unwrappedPhase": Dataset(
                (rows + cols).astype(np.float32), {"units": b"radians"}
            ),
            "coherenceMagnitude": Dataset(
                np.full((8, 9), 0.75, dtype=np.float32),
                {"units": b"1"},
            ),
            "connectedComponents": Dataset(
                np.ones((8, 9), dtype=np.uint16), {"_FillValue": 65535}
            ),
            "ionospherePhaseScreen": Dataset(
                np.full((8, 9), 0.1, dtype=np.float32), {"units": b"radians"}
            ),
            "ionospherePhaseScreenUncertainty": Dataset(
                np.full((8, 9), 0.02, dtype=np.float32), {"units": b"radians"}
            ),
        }
    )

    class Product:
        def __contains__(self, path):
            return path in {
                "/science/LSAR/identification",
                f"/{gunw_access._PHASE_ROOT}",
                f"/{gunw_access._PHASE_ROOT}/HH",
            }

        def __getitem__(self, path):
            return {
                "/science/LSAR/identification": id_group,
                f"/{gunw_access._PHASE_ROOT}": grid,
                f"/{gunw_access._PHASE_ROOT}/HH": data,
            }[path]

    return Product()


def _patch_remote_product(monkeypatch):
    product = _mock_product()
    cache = SimpleNamespace(total_requested_bytes=123456)

    @contextmanager
    def open_remote(url, *, max_range_bytes):
        assert url == PRODUCT_URL
        assert max_range_bytes == gunw_access.MAX_GUNW_WINDOW_RANGE_BYTES
        yield product, cache

    monkeypatch.setattr(gunw_access, "_open_remote_product", open_remote)


@pytest.mark.parametrize(
    "url",
    [
        PRODUCT_URL.replace("https://", "http://"),
        PRODUCT_URL.replace(
            "nisar.asf.earthdatacloud.nasa.gov/",
            "nisar.asf.earthdatacloud.nasa.gov:8443/",
        ),
        PRODUCT_URL + "?token=not-allowed",
        PRODUCT_URL.replace(COLLECTION, "NISAR_L2_GUNW_BETA_V1"),
    ],
)
def test_rejects_noncanonical_gunw_product_urls(url):
    with pytest.raises(GunwAccessError):
        read_gunw_window(
            _feature(url=url),
            polarization="HH",
            rows=slice(0, 2),
            columns=slice(0, 2),
            provider_qa_summary=QA_SUMMARY,
        )


def test_reads_bounded_index_window_and_retains_provider_qa_fail(monkeypatch):
    _patch_remote_product(monkeypatch)

    result = read_gunw_window(
        _feature(),
        polarization="HH",
        rows=slice(2, 5),
        columns=slice(3, 7),
        provider_qa_summary=QA_SUMMARY,
    )

    assert result.arrays["unwrappedPhase"].shape == (3, 4)
    assert result.arrays["unwrappedPhase"].tolist() == [
        [5.0, 6.0, 7.0, 8.0],
        [6.0, 7.0, 8.0, 9.0],
        [7.0, 8.0, 9.0, 10.0],
    ]
    assert result.grid_metadata["epsg_code"] == 32635
    assert result.provider_qa["status"] == "FAIL"
    assert result.access["complete_product_download_requested"] is False
    assert result.access["window_provenance"]["layers"]["mask"]["sha256"]
    assert result.selection_mask is None


def test_reads_optional_ionosphere_layers_only_when_requested(monkeypatch):
    _patch_remote_product(monkeypatch)

    result = read_gunw_window(
        _feature(),
        polarization="HH",
        rows=slice(2, 5),
        columns=slice(3, 7),
        layers=(
            "unwrappedPhase",
            "coherenceMagnitude",
            "connectedComponents",
            "mask",
            "ionospherePhaseScreen",
            "ionospherePhaseScreenUncertainty",
        ),
        provider_qa_summary=QA_SUMMARY,
    )

    assert result.arrays["ionospherePhaseScreen"].shape == (3, 4)
    assert result.arrays["ionospherePhaseScreenUncertainty"].shape == (3, 4)
    assert result.access["window_provenance"]["layers"]["ionospherePhaseScreen"]["sha256"]
    assert result.provider_qa["status"] == "FAIL"


def test_rejects_unpinned_product_specification_before_reading(monkeypatch):
    product = _mock_product()
    product["/science/LSAR/identification"]["productSpecificationVersion"].value = "1.4.0"

    @contextmanager
    def open_remote(_url, *, max_range_bytes):
        yield product, SimpleNamespace(total_requested_bytes=100)

    monkeypatch.setattr(gunw_access, "_open_remote_product", open_remote)
    with pytest.raises(GunwAccessError, match="specification version"):
        read_gunw_window(
            _feature(),
            polarization="HH",
            rows=slice(0, 2),
            columns=slice(0, 2),
            provider_qa_summary=QA_SUMMARY,
        )


def test_gunw_mask_decoder_exposes_source_fields_without_thresholding():
    raw = np.array(
        [[111, 12, 65536 + 111, (1 << 24) + 212, 255]], dtype=np.uint32
    )

    decoded = decode_gunw_mask(raw)

    assert decoded["water_flag"].tolist() == [[1, 0, 1, 2, 2]]
    assert decoded["reference_subswath"].tolist() == [[1, 1, 1, 1, 5]]
    assert decoded["secondary_subswath"].tolist() == [[1, 2, 1, 2, 5]]
    assert decoded["reference_anomaly_flags"][0, 2] == 1
    assert decoded["ionosphere_interpolated"][0, 3]
    assert decoded["fill"].tolist() == [[False, False, False, False, True]]


def test_mask_decoder_rejects_wrong_dtype_and_dimensions():
    with pytest.raises(GunwAccessError, match="uint32"):
        decode_gunw_mask(np.zeros((2, 2), dtype=np.uint8))
    with pytest.raises(GunwAccessError, match="two-dimensional"):
        decode_gunw_mask(np.zeros((2,), dtype=np.uint32))
