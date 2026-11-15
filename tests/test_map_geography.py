import hashlib
import importlib.util
import json
import math
import re
from datetime import datetime, timezone
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
    assert "Antimeridian-crossing rectangles are not supported." in script
    assert "NATURAL EARTH 1:110M COASTLINE" in script
    assert 'const showGeographicFallback=!contextMode&&!challengeMapMode&&!imageURL&&!lastGoodBasemap&&naturalEarthCoastline' in script
    assert '"BlueMarble_NextGeneration"' in script
    assert 'function scheduleBasemapPreload(url,view,mode,date)' in script
    assert 'class="gibs-basemap gibs-basemap-stale"' in script
    assert 'class="gibs-global-base"' in script
    assert "areaBounds?\"REPLACE AREA\"" in script


def test_diagnostic_map_accessibility_survives_control_synchronization():
    script = (ROOT / "echo/static/app.js").read_text()
    assert 'svg.setAttribute("aria-label",mapAccessibilityDescription())' in script
    helper = script.split("function mapAccessibilityDescription() {", 1)[1].split("\n}\n", 1)[0]
    assert "adversarialSpatialView" in helper
    assert "common-support cells shown" in helper
    assert "Provider QA is unresolved; this is not a validated finding." in helper
    assert "Number(cell.common_valid_wtr_area_fraction)>=view.threshold" in helper


def test_retained_opera_pair_timeline_uses_only_review_linked_observations():
    script = (ROOT / "echo/static/app.js").read_text()
    assert "function retainedOperaObservations()" in script
    assert "review?.primary_opera_pair" in script
    assert "function acquisitionTimeFromOperaSceneId(sceneId)" in script
    assert "CASE-LINKED · DIAGNOSTIC" in script
    assert "not an ASF catalog result" in script
    assert 'data-retained-observation-index="${index}"' in script
    assert 'aria-pressed="${selected}"' in script
    assert "openCrossSensorAssessment(investigationButton)" in script
    assert "selectedOperaSeriesComparison()" in script
    assert "No acquisitions in this catalog query." in script
    for case_id in ("rio-grande-do-sul-t163-349925-2024", "rio-grande-do-sul-t024-2024"):
        review = json.loads((ROOT / "data/cases" / case_id / "case-review.json").read_text())
        pair = review["primary_opera_pair"]
        times = []
        for scene_id in (pair["before_scene_id"], pair["after_scene_id"]):
            match = re.search(r"_(\d{8}T\d{6})Z_", scene_id)
            assert match and scene_id.startswith("OPERA_L2_RTC-S1_")
            times.append(datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc))
        assert times[0] < times[1]


def test_retained_opera_timeline_shows_selected_case_scene_details():
    script = (ROOT / "echo/static/app.js").read_text()
    details = script.split("function renderDetails(sceneId=selectedSceneId) {", 1)[1].split(
        "\nfunction ", 1
    )[0]
    workspace = script.split("function renderWorkspace() {", 1)[1].split(
        '\n$("#comparisonPair").addEventListener', 1
    )[0]
    timeline_click = script.split('$("#timelineTrack").addEventListener("click",(event)=>{', 1)[1].split(
        '\n$("#bhoonidhiTimelineTrack")', 1
    )[0]
    assert 'const retained=retainedOperaObservations();' in details
    assert 'CASE-LINKED OBSERVATION ${index+1} OF ${retained.length}' in details
    assert "no consolidated PASS/FAIL verdict" in details
    assert "not an ASF catalog search result" in details
    assert "retainedObservationSelectionIndex=0" in workspace
    assert 'retainedObservationSelectionIndex=Number(retained.dataset.retainedObservationIndex);' in timeline_click
    assert "renderDetails();" in timeline_click


def test_retained_case_map_distinguishes_catalog_footprints_from_linked_measurements():
    script = (ROOT / "echo/static/app.js").read_text()
    caption = script.split("function renderMapCaption() {", 1)[1].split("\n}\n", 1)[0]
    assert "${retainedCaseObservations.length} retained OPERA acquisitions · map backdrop is context only" in caption
    assert "NO SAR MEASUREMENT LAYER" in script
    assert "view the saved SAR measurement and evidence" in script
    assert '"ECHO <span>·</span> OPTICAL CONTEXT · NO SAR LAYER"' in script


def test_retained_case_measurement_is_separated_from_current_catalog_gates():
    script = (ROOT / "echo/static/app.js").read_text()
    caption = script.split("function renderMapCaption() {", 1)[1].split("\n}\n", 1)[0]
    records = script.split("function investigationGateRecords() {", 1)[1].split("\n}\n", 1)[0]
    renderer = script.split("function renderInvestigationGates() {", 1)[1].split("\n}\n", 1)[0]
    assert "retainedCaseMeasurementAvailable=!explorationWorkspace&&!pair&&!worldView&&retainedOperaObservations().length>=2" in records
    assert "!explorationWorkspace&&!worldView&&displayed.length===0" in caption
    assert "No comparison was run for the current catalog selection" in records
    assert '"NEW-PAIR CATALOG GATES"' in renderer
    assert '"SAVED MEASUREMENT AVAILABLE"' in renderer
    assert '"SAVED MEASUREMENT <small>DIAGNOSTIC · QA UNRESOLVED</small>"' in renderer
    assert '$(".confidence-block .readiness-track").hidden=retainedCaseMeasurementAvailable' in renderer
    assert "These four gates apply only to a new catalog pair" in renderer
    assert "View Measurement & Evidence to see the measured SAR response, acquisition dates, QA, and limits" in renderer
