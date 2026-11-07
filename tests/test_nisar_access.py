from datetime import datetime, timezone
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from echo.nisar_access import (
    MAX_METADATA_RANGE_BYTES,
    NisarAccessError,
    REMOTE_BLOCK_BYTES,
    _install_read_budget,
    inspect_identification,
    read_gcov_window,
)


SCENE_ID = (
    "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_"
    "20260819T233953_P05023_N_F_J_001"
)
PRODUCT_URL = (
    "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
    f"NISAR_L2_GCOV_PROVISIONAL_V1/{SCENE_ID}/{SCENE_ID}.h5"
)


def _feature(*, scene_id=SCENE_ID, url=PRODUCT_URL):
    return {
        "properties": {
            "fileID": scene_id,
            "url": url,
            "processingLevel": "GCOV",
            "collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1",
        }
    }


@pytest.mark.parametrize(
    "url",
    [
        PRODUCT_URL.replace("https://", "http://"),
        PRODUCT_URL.replace(
            "nisar.asf.earthdatacloud.nasa.gov/",
            "nisar.asf.earthdatacloud.nasa.gov:8443/",
        ),
        PRODUCT_URL.replace("nisar.asf.earthdatacloud.nasa.gov", "example.com"),
        "https://[malformed/NISAR/product.h5",
        PRODUCT_URL + "?token=must-not-be-accepted",
        PRODUCT_URL.replace(f"/{SCENE_ID}.h5", "/another-file.h5"),
    ],
)
def test_rejects_product_urls_outside_the_catalog_allowlist(url):
    with pytest.raises(NisarAccessError):
        inspect_identification(_feature(url=url))


def test_rejects_scene_id_that_is_not_nisar_l2_gcov():
    with pytest.raises(NisarAccessError, match="not a NISAR L2 GCOV"):
        inspect_identification(_feature(scene_id="other-scene"))


def test_rejects_catalog_collections_outside_supported_asf_gcov_versions():
    feature = _feature()
    feature["properties"]["collectionName"] = "UNRELATED_COLLECTION"
    with pytest.raises(NisarAccessError, match="supported ASF GCOV"):
        inspect_identification(feature)


def test_accepts_validated_gcov_collection_url():
    feature = _feature(
        url=PRODUCT_URL.replace(
            "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_GCOV_V1"
        )
    )
    feature["properties"]["collectionName"] = "NISAR_L2_GCOV_V1"
    from echo.nisar_access import _validated_product

    scene_id, url, instrument = _validated_product(feature)

    assert scene_id == SCENE_ID
    assert "/NISAR/NISAR_L2_GCOV_V1/" in url
    assert instrument == "LSAR"


def test_reads_only_allowlisted_identification_datasets(monkeypatch):
    opened = {}
    read_fields = []

    class Dataset:
        def __init__(self, value):
            self.value = value

        def __getitem__(self, key):
            assert key == ()
            return self.value

    class Group(dict):
        def __getitem__(self, key):
            read_fields.append(key)
            return super().__getitem__(key)

    class Product:
        def __init__(self, _file, mode):
            assert mode == "r"

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

        def __getitem__(self, path):
            assert path == "/science/LSAR/identification"
            return Group(
                {
                    "instrumentName": Dataset(b"LSAR"),
                    "listOfObservationModes": Dataset([b"(NOT SPECIFIED)"]),
                    "trackNumber": Dataset(98),
                    "unlistedLargeDataset": Dataset(b"not read"),
                }
            )

    class RemoteFile:
        cache = SimpleNamespace(
            total_requested_bytes=65536,
            fetcher=lambda _start, _end: b"",
        )

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

    class FileSystem:
        client_kwargs = {"headers": {"Authorization": "secret test value"}}

        def open(self, path, mode, *, block_size, cache_type):
            opened.update(
                path=path,
                mode=mode,
                block_size=block_size,
                cache_type=cache_type,
            )
            return RemoteFile()

    class Auth:
        authenticated = True

    fake_earthaccess = SimpleNamespace(
        login=lambda **kwargs: (opened.update(login=kwargs) or Auth()),
        get_fsspec_https_session=lambda: FileSystem(),
    )
    fake_h5py = SimpleNamespace(File=Product)
    monkeypatch.setitem(sys.modules, "earthaccess", fake_earthaccess)
    monkeypatch.setitem(sys.modules, "h5py", fake_h5py)

    record = inspect_identification(
        _feature(), inspected_at=datetime(2026, 11, 7, tzinfo=timezone.utc)
    )

    assert opened["login"] == {"strategy": "netrc", "persist": False}
    assert opened["block_size"] == REMOTE_BLOCK_BYTES
    assert opened["cache_type"] == "bytes"
    assert read_fields == [
        "instrumentName",
        "listOfObservationModes",
        "trackNumber",
    ]
    assert record["product"]["metadata"]["instrumentName"] == "LSAR"
    assert record["product"]["metadata"]["listOfObservationModes"] == [
        "(NOT SPECIFIED)"
    ]
    assert record["access"]["radar_measurement_arrays_read"] is False
    assert record["access"]["complete_product_download_requested"] is False
    assert record["access"]["fsspec_range_bytes_requested"] == 65536
    assert record["access"]["max_fsspec_range_bytes_requested"] == MAX_METADATA_RANGE_BYTES
    assert "url" not in record["product"]
    assert "secret test value" not in repr(record)


def test_range_reader_aborts_before_exceeding_total_metadata_budget():
    cache = SimpleNamespace(
        total_requested_bytes=MAX_METADATA_RANGE_BYTES + 1,
        fetcher=lambda _start, _end: pytest.fail("over-budget range must not be fetched"),
    )
    remote_file = SimpleNamespace(cache=cache)
    _install_read_budget(remote_file)

    with pytest.raises(NisarAccessError, match="budget exceeded"):
        cache.fetcher(0, 1024)


def test_fails_closed_when_earthdata_authentication_is_unavailable(monkeypatch):
    called = False

    class Auth:
        authenticated = False

    def filesystem_must_not_be_opened():
        nonlocal called
        called = True
        raise AssertionError("filesystem must not be requested without authentication")

    fake_earthaccess = SimpleNamespace(
        login=lambda **_kwargs: Auth(),
        get_fsspec_https_session=filesystem_must_not_be_opened,
    )
    monkeypatch.setitem(sys.modules, "earthaccess", fake_earthaccess)
    monkeypatch.setitem(sys.modules, "h5py", SimpleNamespace())

    with pytest.raises(NisarAccessError, match="local netrc"):
        inspect_identification(_feature())
    assert called is False


def test_reads_only_requested_allowlisted_gcov_window(monkeypatch):
    source = np.arange(72, dtype=np.float32).reshape(8, 9)
    read_requests = []

    class Dataset:
        shape = source.shape
        dtype = source.dtype

        def __getitem__(self, selection):
            read_requests.append(selection)
            return source[selection]

    class CoordinateDataset:
        def __init__(self, values):
            self.values = values
            self.shape = values.shape
            self.dtype = values.dtype

        def __getitem__(self, selection):
            read_requests.append(selection)
            return self.values[selection]

    class ProjectionDataset:
        attrs = {"epsg_code": 32636, "grid_mapping_name": "transverse_mercator"}

        def __getitem__(self, selection):
            assert selection == ()
            return 32636

    class Product:
        def __init__(self, _file, mode):
            assert mode == "r"

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

        def __getitem__(self, path):
            assert path == "/science/LSAR/GCOV/grids/frequencyA"
            return {
                "HHHH": Dataset(),
                "mask": Dataset(),
                "projection": ProjectionDataset(),
                "xCoordinates": CoordinateDataset(np.arange(9, dtype=np.float64)),
                "yCoordinates": CoordinateDataset(np.arange(8, 0, -1, dtype=np.float64)),
            }

    class RemoteFile:
        cache = SimpleNamespace(total_requested_bytes=32768, fetcher=lambda *_: b"")

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

    class FileSystem:
        client_kwargs = {}

        def open(self, path, mode, *, block_size, cache_type):
            assert path == PRODUCT_URL
            assert mode == "rb"
            assert block_size == REMOTE_BLOCK_BYTES
            assert cache_type == "bytes"
            return RemoteFile()

    class Auth:
        authenticated = True

    def login(**kwargs):
        assert kwargs == {"strategy": "netrc", "persist": False}
        return Auth()

    monkeypatch.setitem(
        sys.modules,
        "earthaccess",
        SimpleNamespace(
            login=login,
            get_fsspec_https_session=FileSystem,
        ),
    )
    monkeypatch.setitem(sys.modules, "h5py", SimpleNamespace(File=Product))

    window = read_gcov_window(
        _feature(),
        frequency="A",
        rows=slice(2, 4),
        columns=slice(3, 6),
        layers=("HHHH", "mask"),
    )

    expected = source[2:4, 3:6]
    np.testing.assert_array_equal(window.layers["HHHH"], expected)
    np.testing.assert_array_equal(window.layers["mask"], expected)
    assert window.scene_id == SCENE_ID
    assert window.catalog_metadata["collectionName"] == "NISAR_L2_GCOV_PROVISIONAL_V1"
    assert window.catalog_metadata["fileID"] == SCENE_ID
    assert window.row_start == 2 and window.row_stop == 4
    assert window.column_start == 3 and window.column_stop == 6
    assert read_requests[:2] == [(slice(2, 4), slice(3, 6))] * 2
    np.testing.assert_array_equal(window.grid_metadata["x_coordinates"], [3, 4, 5])
    np.testing.assert_array_equal(window.grid_metadata["y_coordinates"], [6, 5])
    assert window.grid_metadata["projection_attributes"]["epsg_code"] == 32636
    assert window.access["fsspec_range_bytes_requested"] == 32768
    assert window.access["complete_product_download_requested"] is False
    assert window.access["window_sample_count"] == 6


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"frequency": "C"}, "frequency must be A or B"),
        ({"rows": slice(-1, 2)}, "explicit non-negative bounds"),
        ({"rows": slice(0, 2, 2)}, "unit-step slice"),
        ({"layers": ("arbitraryDataset",)}, "not allowlisted"),
        ({"rows": slice(0, 513), "columns": slice(0, 513)}, "sample limit"),
    ],
)
def test_window_request_bounds_and_allowlists_fail_before_remote_access(kwargs, message):
    options = {
        "frequency": "A",
        "rows": slice(0, 2),
        "columns": slice(0, 2),
        "layers": ("HHHH",),
    }
    options.update(kwargs)
    with pytest.raises(NisarAccessError, match=message):
        read_gcov_window(_feature(), **options)
