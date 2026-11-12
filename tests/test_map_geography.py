import hashlib
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE_HASH = "664449b39070027e882abb295974d182afec18ca21107273d17e9e8bf6f64817"
DERIVED_HASH = "666276f959174a1355a406ea5415ede184e92775c65dd4e8279623489bc01776"


def _converter_module():
    spec = importlib.util.spec_from_file_location(
        "build_natural_earth_coastline", ROOT / "tools/research/build_natural_earth_coastline.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retained_natural_earth_layer_is_reproducible_and_bounded():
    source = ROOT / "data/basemap/natural-earth-110m-coastline.zip"
    output = ROOT / "echo/static/natural-earth-coastline-110m.json"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_HASH
    encoded = output.read_bytes()
    assert hashlib.sha256(encoded).hexdigest() == DERIVED_HASH
    record = json.loads(encoded)
    assert record["type"] == "FeatureCollection"
    assert len(record["features"]) == 134
    point_count = 0
    for feature in record["features"]:
        assert feature["geometry"]["type"] == "MultiLineString"
        for line in feature["geometry"]["coordinates"]:
            assert len(line) >= 2
            point_count += len(line)
            for longitude, latitude in line:
                assert math.isfinite(longitude) and math.isfinite(latitude)
                assert -180 <= longitude <= 180
                assert -90 <= latitude <= 90
    assert point_count == 5128
    assert _converter_module().build()["features"] == record["features"]


def test_global_map_and_antimeridian_limits_are_explicit_in_ui():
    script = (ROOT / "echo/static/app.js").read_text()
    page = (ROOT / "echo/static/index.html").read_text()
    assert 'id="worldView"' in page
    assert "worldView=true;zoom=1;mapPan=[0,0]" in script
    assert "Split it into two non-wrapping WGS84 searches." in script
    assert "NATURAL EARTH 1:110M COASTLINE" in script
    assert "const showGeographicFallback=!contextMode&&!challengeMapMode&&!imageURL&&naturalEarthCoastline" in script
    assert "areaBounds?\"REPLACE AREA\"" in script
