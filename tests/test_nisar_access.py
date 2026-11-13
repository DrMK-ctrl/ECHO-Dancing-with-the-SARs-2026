from datetime import datetime, timezone
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from echo.nisar_access import (
    MAX_METADATA_RANGE_BYTES,
    MAX_WINDOW_SAMPLES,
    NisarAccessError,
    REMOTE_BLOCK_BYTES,
    _is_retryable_remote_range_failure,
    _install_read_budget,
    _open_remote_product,
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


def test_range_budget_records_bounded_fetch_count_and_elapsed_time():
    cache = SimpleNamespace(
        total_requested_bytes=0,
        fetcher=lambda start, end: bytes(end - start),
    )
    remote_file = SimpleNamespace(cache=cache)

    _install_read_budget(remote_file, limit_bytes=16)
    assert cache.fetcher(0, 8) == bytes(8)

    assert cache.remote_fetch_count == 1
    assert cache.remote_fetch_elapsed_seconds >= 0


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


def test_remote_transport_reset_retains_consumed_range_bytes_for_bounded_retry(monkeypatch):
    class Cache:
        total_requested_bytes = 4096

        @staticmethod
        def fetcher(*_args):
            raise ConnectionResetError("provider closed the range connection")

    class RemoteFile:
        cache = Cache()

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

    class FileSystem:
        client_kwargs = {}

        def open(self, _url, _mode, *, block_size, cache_type):
            assert block_size == REMOTE_BLOCK_BYTES
            assert cache_type == "bytes"
            return RemoteFile()

    class Product:
        def __init__(self, _remote, mode):
            assert mode == "r"

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

    class Auth:
        authenticated = True

    monkeypatch.setitem(
        sys.modules,
        "earthaccess",
        SimpleNamespace(
            login=lambda **_kwargs: Auth(),
            get_fsspec_https_session=lambda: FileSystem(),
        ),
    )
    monkeypatch.setitem(sys.modules, "h5py", SimpleNamespace(File=Product))

    with pytest.raises(NisarAccessError) as captured:
        with _open_remote_product(
            PRODUCT_URL,
            max_range_bytes=MAX_METADATA_RANGE_BYTES,
            block_size=REMOTE_BLOCK_BYTES,
        ) as (_product, cache):
            cache.fetcher(0, 16)

    assert captured.value.remote_range_bytes_requested == 4096
    assert captured.value.remote_range_request_count == 1
    assert captured.value.remote_range_fetch_elapsed_seconds >= 0
    assert _is_retryable_remote_range_failure(captured.value)

    non_transport = NisarAccessError("invalid HDF5 dataset")
    non_transport.remote_range_bytes_requested = 4096
    assert not _is_retryable_remote_range_failure(non_transport)


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


def test_range_reader_rejects_a_range_that_would_cross_the_budget():
    cache = SimpleNamespace(
        total_requested_bytes=MAX_METADATA_RANGE_BYTES - 100,
        fetcher=lambda _start, _end: pytest.fail("budget-crossing range must not be fetched"),
    )
    remote_file = SimpleNamespace(cache=cache)
    _install_read_budget(remote_file)

    with pytest.raises(NisarAccessError, match="budget exceeded"):
        cache.fetcher(0, 101)


def test_range_reader_rejects_a_range_that_would_cross_the_budget():
    cache = SimpleNamespace(
        total_requested_bytes=MAX_METADATA_RANGE_BYTES - 100,
        fetcher=lambda _start, _end: pytest.fail("budget-crossing range must not be fetched"),
    )
    remote_file = SimpleNamespace(cache=cache)
    _install_read_budget(remote_file)

    with pytest.raises(NisarAccessError, match="budget exceeded"):
        cache.fetcher(0, 101)


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

        def __init__(self, attrs=None):
            self.attrs = attrs or {}

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
                "inputDataExceptionMask": Dataset(
                    {
                        "description": b"documented exception and validity flags",
                        "valid_min": np.uint16(0),
                    }
                ),
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
        layers=("HHHH", "mask", "inputDataExceptionMask"),
    )

    expected = source[2:4, 3:6]
    np.testing.assert_array_equal(window.layers["HHHH"], expected)
    np.testing.assert_array_equal(window.layers["mask"], expected)
    assert window.layer_attributes["inputDataExceptionMask"] == {
        "description": "documented exception and validity flags",
        "valid_min": 0,
    }
    assert window.scene_id == SCENE_ID
    assert window.catalog_metadata["collectionName"] == "NISAR_L2_GCOV_PROVISIONAL_V1"
    assert window.catalog_metadata["fileID"] == SCENE_ID
    assert window.row_start == 2 and window.row_stop == 4
    assert window.column_start == 3 and window.column_stop == 6
    assert read_requests[:3] == [(slice(2, 4), slice(3, 6))] * 3
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
        ({"max_samples": 0}, "max_samples must be between 1"),
        ({"_remote_block_bytes": 1}, "remote block size is outside the bounded allowlist"),
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


def test_reads_geographic_bbox_window_with_exact_pixel_center_mask(monkeypatch):
    from pyproj import Transformer

    from echo.geospatial import select_geographic_bbox_window

    forward = Transformer.from_crs(4326, 32736, always_xy=True)
    center_x, center_y = forward.transform(33.0, -24.0)
    x_coordinates = center_x + np.arange(9, dtype=np.float64) * 100 - 400
    y_coordinates = center_y + np.arange(8, dtype=np.float64) * 100 - 350
    source = np.arange(72, dtype=np.float32).reshape(8, 9)
    reads = []

    class Dataset:
        def __init__(self, values, attrs=None):
            self.values = values
            self.shape = np.shape(values)
            self.dtype = np.asarray(values).dtype
            self.attrs = attrs or {}

        def __getitem__(self, selection):
            reads.append(selection)
            if selection == ():
                return self.values
            return np.asarray(self.values)[selection]

    group = {
        "HHHH": Dataset(source),
        "projection": Dataset(32736, {"epsg_code": 32736}),
        "xCoordinates": Dataset(x_coordinates),
        "yCoordinates": Dataset(y_coordinates),
    }

    class Product:
        def __init__(self, _file, mode):
            assert mode == "r"

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

        def __getitem__(self, path):
            assert path == "/science/LSAR/GCOV/grids/frequencyA"
            return group

    class RemoteFile:
        cache = SimpleNamespace(total_requested_bytes=65536, fetcher=lambda *_: b"")

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

    class FileSystem:
        client_kwargs = {}

        def open(self, *_args, **_kwargs):
            return RemoteFile()

    class Auth:
        authenticated = True

    monkeypatch.setitem(
        sys.modules,
        "earthaccess",
        SimpleNamespace(login=lambda **_: Auth(), get_fsspec_https_session=FileSystem),
    )
    monkeypatch.setitem(sys.modules, "h5py", SimpleNamespace(File=Product))
    bounds = (32.998, -24.002, 33.002, -23.998)
    selection = select_geographic_bbox_window(
        x_coordinates,
        y_coordinates,
        epsg_code=32736,
        bounds_wgs84=bounds,
        max_samples=MAX_WINDOW_SAMPLES,
    )

    window = read_gcov_window(
        _feature(),
        frequency="A",
        bounds_wgs84=bounds,
        layers=("HHHH",),
    )

    np.testing.assert_array_equal(
        window.layers["HHHH"],
        source[selection.row_start : selection.row_stop, selection.column_start : selection.column_stop],
    )
    np.testing.assert_array_equal(window.selection_mask, selection.mask)
    assert window.selection_metadata["bounds_wgs84"] == list(bounds)
    assert window.access["full_grid_coordinate_bytes_read_for_selection"] == (
        x_coordinates.nbytes + y_coordinates.nbytes
    )
    assert window.row_start == selection.row_start
    assert window.column_start == selection.column_start
    assert reads.count(slice(None, None, None)) == 2
