import json
from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from pyproj import Transformer
import h5py

from echo.opera_rtc import (
    analyze_opera_rtc_s1_pair,
    common_opera_rtc_s1_clear_mask,
    decode_opera_rtc_s1_mask,
)
from echo.opera_rtc_access import (
    MAX_RTC_S1_ASSET_BYTES,
    OperaRtcS1AccessError,
    read_opera_rtc_s1_window,
)
from echo.opera_rtc_analysis import (
    OperaRtcS1AnalysisError,
    build_opera_rtc_s1_pair_analysis,
)


class _FixtureResponse:
    def __init__(self, payload=b"", *, status=206, headers=None):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size):
        for start in range(0, len(self.payload), chunk_size):
            yield self.payload[start : start + chunk_size]


class _FixtureSession:
    def __init__(self, assets):
        self.assets = assets
        self.urls_read = []
        self.ranges_read = []

    def get(self, url, *, headers, stream, timeout):
        start, end = map(int, headers["Range"].removeprefix("bytes=").split("-"))
        self.urls_read.append(url)
        self.ranges_read.append((url, headers["Range"]))
        payload = self.assets[url][start : end + 1]
        total_size = len(self.assets[url])
        return _FixtureResponse(
            payload,
            headers={
                "Content-Range": f"bytes {start}-{start + len(payload) - 1}/{total_size}"
            },
        )


class _DeniedSession:
    def get(self, _url, **_kwargs):
        response = _FixtureResponse(status=401)
        response.history = [
            SimpleNamespace(
                url="https://urs.earthdata.nasa.gov/oauth/authorize?state=private-state"
            )
        ]
        response.url = (
            "https://cumulus.asf.alaska.edu/login?error=access_denied"
            "&error_msg=private-detail"
        )
        return response


def _geotiff(values, *, dtype, transform=None):
    with MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            height=values.shape[0],
            width=values.shape[1],
            count=1,
            dtype=dtype,
            crs="EPSG:32722",
            transform=transform or from_origin(500000, 6700000, 30, 30),
        ) as dataset:
            dataset.write(values.astype(dtype), 1)
        return memory.read()


def _hdf5_metadata():
    buffer = BytesIO()
    with h5py.File(buffer, "w") as product:
        qa = product.create_group("metadata/qa")
        for name, value in (
            ("geometricAccuracy/bias/x", -0.72),
            ("geometricAccuracy/bias/y", -0.67),
            ("geometricAccuracy/stddev/x", 0.7),
            ("geometricAccuracy/stddev/y", 0.62),
            ("rfi/isRfiInfoAvailable", True),
            ("rfi/rfiMitigationDomain", np.bytes_("TimeAndFrequency")),
            ("rfi/rfiMitigationPerformed", np.bytes_("BasedOnNoiseMeas")),
            ("rfi/rfiBurstReport/azimuthTime", np.bytes_("2024-05-11T08:49:44Z")),
            ("rfi/rfiBurstReport/swath", np.bytes_("IW1")),
            ("rfi/rfiBurstReport/inBandOutBandPowerRatio", 13.10681),
        ):
            parent, _, leaf = name.rpartition("/")
            qa.require_group(parent).create_dataset(leaf, data=value)
        algorithms = product.create_group("metadata/processingInformation/algorithms")
        algorithms.create_dataset("softwareVersion", data=np.bytes_("1.0.2"))
        algorithms.create_dataset("isce3Version", data=np.bytes_("0.15.0"))
    return buffer.getvalue()


def _feature_with_assets(
    measurement_bytes,
    mask_bytes,
    *,
    scene_id=(
        "OPERA_L2_RTC-S1_T024-050660-IW1_20240511T084944Z_"
        "20240512T065737Z_S1A_30_v1.0"
    ),
    start_time="2024-05-11T08:49:44Z",
    stop_time="2024-05-11T08:49:47Z",
):
    measurement_name = f"{scene_id}_VV.tif"
    mask_name = f"{scene_id}_mask.tif"
    metadata_name = f"{scene_id}.h5"
    metadata_bytes = _hdf5_metadata()
    return {
        "type": "Feature",
        "properties": {
            "fileID": scene_id,
            "url": f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_VH.tif",
            "startTime": start_time,
            "stopTime": stop_time,
            "bytes": {
                measurement_name: {"bytes": len(measurement_bytes), "format": "GeoTIFF"},
                mask_name: {"bytes": len(mask_bytes), "format": "GeoTIFF"},
                metadata_name: {"bytes": len(metadata_bytes), "format": "HDF5"},
            },
        },
        "geometry": None,
    }


def _one_pixel_bounds():
    inverse = Transformer.from_crs("EPSG:32722", "EPSG:4326", always_xy=True)
    lon, lat = inverse.transform(500045, 6699955)
    return (lon - 0.00004, lat - 0.00004, lon + 0.00004, lat + 0.00004)


def test_authenticated_window_reader_derives_allowlisted_assets_and_bounds_aoi():
    power_bytes = _geotiff(np.arange(1, 17).reshape(4, 4), dtype="float32")
    source_mask = np.zeros((4, 4), dtype=np.uint8)
    source_mask[1, 1] = 1
    mask_bytes = _geotiff(source_mask, dtype="uint8")
    feature = _feature_with_assets(power_bytes, mask_bytes)
    scene_id = feature["properties"]["fileID"]
    measurement_url = (
        "https://datapool.asf.alaska.edu/RTC/OPERA-S1/"
        f"{scene_id}_VV.tif"
    )
    mask_url = (
        "https://datapool.asf.alaska.edu/RTC/OPERA-S1/"
        f"{scene_id}_mask.tif"
    )
    metadata_url = f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}.h5"
    session = _FixtureSession(
        {measurement_url: power_bytes, mask_url: mask_bytes, metadata_url: _hdf5_metadata()}
    )

    result = read_opera_rtc_s1_window(
        feature,
        bounds_wgs84=_one_pixel_bounds(),
        polarization="VV",
        http_session=session,
    )

    assert result.scene_id == scene_id
    assert result.polarization == "VV"
    assert result.grid["crs"] == "EPSG:32722"
    assert result.grid["window"]["selected_pixel_center_count"] == 1
    assert result.values.shape == result.mask.shape == result.selection_mask.shape
    assert result.values.shape == (1, 1)
    assert result.mask.tolist() == [[1]]
    assert result.source["mission"] == "Sentinel-1"
    assert result.source["provider_qa_disposition"] == "NO_CONSOLIDATED_PASS_FAIL_FIELD_IN_RETRIEVED_HDF5"
    assert result.source["quality_metadata"]["radio_frequency_interference"]["rfi_info_available"]["value"] is True
    assert result.source["quality_metadata"]["processing_information"]["algorithms"]["softwareVersion"] == "1.0.2"
    assert result.access["source_assets_written_to_disk"] is False
    assert result.access["authentication"] == "NOT_AUTHENTICATED_TEST_INJECTION"
    assert result.access["network_retrieval"] is False
    assert result.access["measurement_bytes"] == len(power_bytes)
    assert set(session.urls_read) == {measurement_url, mask_url, metadata_url}
    assert set(session.ranges_read) == {
        (measurement_url, f"bytes=0-{len(power_bytes) - 1}"),
        (mask_url, f"bytes=0-{len(mask_bytes) - 1}"),
        (metadata_url, f"bytes=0-{len(_hdf5_metadata()) - 1}"),
    }
    assert result.assets["measurement"]["sha256"]
    assert result.assets["mask"]["sha256"]
    assert result.assets["metadata"]["sha256"]


def test_window_reader_rejects_over_limit_catalog_asset_before_network_read():
    power_bytes = b"small-fixture"
    mask_bytes = b"mask-fixture"
    feature = _feature_with_assets(power_bytes, mask_bytes)
    scene_id = feature["properties"]["fileID"]
    feature["properties"]["bytes"][f"{scene_id}_VV.tif"]["bytes"] = (
        MAX_RTC_S1_ASSET_BYTES + 1
    )
    session = _FixtureSession({})

    with pytest.raises(OperaRtcS1AccessError, match="byte read limit"):
        read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=session,
        )
    assert session.urls_read == []


def test_window_reader_rejects_misaligned_measurement_and_mask_cogs():
    power_bytes = _geotiff(np.ones((4, 4)), dtype="float32")
    mask_bytes = _geotiff(
        np.zeros((4, 4)),
        dtype="uint8",
        transform=from_origin(500030, 6700000, 30, 30),
    )
    feature = _feature_with_assets(power_bytes, mask_bytes)
    scene_id = feature["properties"]["fileID"]
    urls = {
        f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_VV.tif": power_bytes,
        f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_mask.tif": mask_bytes,
        f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}.h5": _hdf5_metadata(),
    }

    with pytest.raises(OperaRtcS1AccessError, match="not exactly aligned"):
        read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=_FixtureSession(urls),
        )


@pytest.mark.parametrize(
    "url, message",
    [
        (
            "https://user@datapool.asf.alaska.edu/RTC/OPERA-S1/"
            "OPERA_L2_RTC-S1_T024-050660-IW1_20240511T084944Z_"
            "20240512T065737Z_S1A_30_v1.0_VH.tif",
            "outside the supported host/path",
        ),
        (
            "https://example.org/RTC/OPERA-S1/scene_VH.tif",
            "outside the supported host/path",
        ),
    ],
)
def test_window_reader_rejects_untrusted_asset_urls(url, message):
    power = _geotiff(np.ones((4, 4)), dtype="float32")
    mask = _geotiff(np.zeros((4, 4)), dtype="uint8")
    feature = _feature_with_assets(power, mask)
    feature["properties"]["url"] = url
    with pytest.raises(OperaRtcS1AccessError, match=message):
        read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=_FixtureSession({}),
        )


def test_window_reader_rejects_affine_spacing_inconsistent_with_scene_id():
    power = _geotiff(
        np.ones((4, 4)), dtype="float32", transform=from_origin(500000, 6700000, 20, 20)
    )
    mask = _geotiff(
        np.zeros((4, 4)), dtype="uint8", transform=from_origin(500000, 6700000, 20, 20)
    )
    feature = _feature_with_assets(power, mask)
    scene_id = feature["properties"]["fileID"]
    urls = {
        f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_VV.tif": power,
        f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_mask.tif": mask,
        f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}.h5": _hdf5_metadata(),
    }

    with pytest.raises(OperaRtcS1AccessError, match="pixel spacing differs"):
        read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=_FixtureSession(urls),
        )


def test_window_reader_rejects_catalog_time_mismatch_before_asset_access():
    power = _geotiff(np.ones((4, 4)), dtype="float32")
    mask = _geotiff(np.zeros((4, 4)), dtype="uint8")
    feature = _feature_with_assets(power, mask, start_time="2024-05-12T08:49:44Z")
    session = _FixtureSession({})

    with pytest.raises(OperaRtcS1AccessError, match="does not match the RTC-S1 scene identifier"):
        read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=session,
        )
    assert session.urls_read == []


def test_window_reader_reports_provider_auth_denial_without_echoing_asset_url():
    power = _geotiff(np.ones((4, 4)), dtype="float32")
    mask = _geotiff(np.zeros((4, 4)), dtype="uint8")
    feature = _feature_with_assets(power, mask)

    with pytest.raises(
        OperaRtcS1AccessError,
        match=r"ASF denied authenticated measurement asset access \(HTTP 401\).*ASF data EULA acceptance.*Cumulus application access",
    ) as error:
        read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=_DeniedSession(),
        )
    assert "datapool" not in str(error.value)
    assert "private-state" not in str(error.value)
    assert "private-detail" not in str(error.value)


def test_pair_manifest_labels_fixture_data_and_links_input_checksums():
    before_power = np.arange(1, 17, dtype=np.float32).reshape(4, 4)
    after_power = before_power * 2
    clear_mask = np.zeros((4, 4), dtype=np.uint8)
    before_data = _geotiff(before_power, dtype="float32")
    after_data = _geotiff(after_power, dtype="float32")
    mask_data = _geotiff(clear_mask, dtype="uint8")
    after_scene = (
        "OPERA_L2_RTC-S1_T024-050660-IW1_20240604T084943Z_"
        "20240612T003018Z_S1A_30_v1.0"
    )
    before_feature = _feature_with_assets(before_data, mask_data)
    after_feature = _feature_with_assets(
        after_data,
        mask_data,
        scene_id=after_scene,
        start_time="2024-06-04T08:49:43Z",
        stop_time="2024-06-04T08:49:46Z",
    )

    def read_fixture(feature, data):
        scene_id = feature["properties"]["fileID"]
        urls = {
            f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_VV.tif": data,
            f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_mask.tif": mask_data,
            f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}.h5": _hdf5_metadata(),
        }
        return read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=_FixtureSession(urls),
        )

    before = read_fixture(before_feature, before_data)
    after = read_fixture(after_feature, after_data)
    record = build_opera_rtc_s1_pair_analysis(before, after)

    assert record["status"] == "FIXTURE_DATA_COMPUTATION_NOT_SCIENTIFIC_RESULT"
    assert record["source_products"]["before"]["scene_id"] == before.scene_id
    assert record["source_products"]["after"]["scene_id"] == after.scene_id
    assert record["provider_qa"]["status"] == "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
    assert record["provider_qa"]["before"] == "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
    assert record["measurement"]["measured_pixel_count"] == 1
    assert record["acquisition_interval_days"] == pytest.approx(24)
    assert record["measurement"]["values_db"][0][0] == pytest.approx(
        10 * np.log10(2)
    )
    assert record["checksums"]["before_values_sha256"]
    assert record["checksums"]["after_values_sha256"]
    json.dumps(record, allow_nan=False)


def test_pair_manifest_rejects_different_burst_identity():
    power = _geotiff(np.ones((4, 4)), dtype="float32")
    mask = _geotiff(np.zeros((4, 4)), dtype="uint8")
    before_feature = _feature_with_assets(power, mask)
    after_scene = (
        "OPERA_L2_RTC-S1_T024-050661-IW1_20240604T084943Z_"
        "20240612T003018Z_S1A_30_v1.0"
    )
    after_feature = _feature_with_assets(
        power, mask, scene_id=after_scene, start_time="2024-06-04T08:49:43Z"
    )

    def window(feature):
        scene_id = feature["properties"]["fileID"]
        urls = {
            f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_VV.tif": power,
            f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_mask.tif": mask,
            f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}.h5": _hdf5_metadata(),
        }
        return read_opera_rtc_s1_window(
            feature,
            bounds_wgs84=_one_pixel_bounds(),
            polarization="VV",
            http_session=_FixtureSession(urls),
        )

    with pytest.raises(OperaRtcS1AnalysisError, match="burst values do not match"):
        build_opera_rtc_s1_pair_analysis(window(before_feature), window(after_feature))


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
