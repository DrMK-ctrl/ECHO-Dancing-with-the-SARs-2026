#!/usr/bin/env python3
"""Replay a retained authentic GCOV window through the local UI in Firefox.

Catalog and preview responses are served from local JSON records so the browser
check exercises the real search, timeline, raster, QA, and pixel-inspection flow
without another provider request. The ECHO server must already be running.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from check_map_area_browser import WebDriver, find_geckodriver, get_free_port
from check_observation_challenge_browser import require_loopback_url


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_URL = "http://127.0.0.1:8766/?case_id=iraq-2026-nisar-gcov-diagnostic"
DEFAULT_PREVIEW = ROOT / "data/research/beirut-nisar-gcov-diagnostic-preview-current-source-2026-11-13.json"
DEFAULT_CATALOG = ROOT / "data/research/beirut-nisar-gcov-catalog-search-2026-11-13.json"
def canonical_json_sha256(value: Any) -> str:
    def normalize(item: Any) -> Any:
        if isinstance(item, dict):
            return {str(key): normalize(child) for key, child in item.items()}
        if isinstance(item, list):
            return [normalize(child) for child in item]
        if (
            isinstance(item, float)
            and item.is_integer()
            and abs(item) <= 9_007_199_254_740_991
        ):
            return int(item)
        return item

    encoded = json.dumps(
        normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def wait_for(driver: WebDriver, session_id: str, script: str, timeout: float = 35) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = driver.execute(session_id, script)
        if value:
            return value
        time.sleep(0.12)
    raise TimeoutError(f"Browser condition timed out: {script}")


def set_value(driver: WebDriver, session_id: str, selector: str, value: Any) -> None:
    driver.request(
        f"/session/{session_id}/execute/sync",
        method="POST",
        payload={
            "script": 'const e=document.querySelector(arguments[0]);e.value=arguments[1];'
            'e.dispatchEvent(new Event("input",{bubbles:true}));'
            'e.dispatchEvent(new Event("change",{bubbles:true}));return e.value',
            "args": [selector, str(value)],
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--geckodriver")
    parser.add_argument("--preview", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument(
        "--require-source-attributes",
        action="store_true",
        help="fail unless the preview contains hashed measurement-dataset attributes",
    )
    args = parser.parse_args()
    require_loopback_url(args.url, parser)
    preview = json.loads(args.preview.read_text(encoding="utf-8"))
    retained_catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    scene_id = preview.get("source", {}).get("scene_id")
    if (
        preview.get("record_type") != "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW"
        or not isinstance(scene_id, str)
        or not scene_id.startswith("NISAR_L2_PR_GCOV_")
        or preview.get("source", {}).get("provider_qa_status") != "FAIL"
        or preview.get("scientific_disposition") != "QA_HELD_DIAGNOSTIC_PREVIEW"
    ):
        parser.error("preview file must be a QA-held real NISAR L2 GCOV observation")
    feature = next(
        (
            item for item in retained_catalog["features"]
            if item.get("properties", {}).get("fileID") == scene_id
        ),
        None,
    )
    if feature is None:
        parser.error("the retained catalog does not contain the preview scene")
    bounds = preview["access"]["geographic_selection"]["bounds_wgs84"]
    catalog_query = retained_catalog.get("query") or retained_catalog.get("catalog_query") or {}
    catalog_source = retained_catalog.get("source") or {}
    feature_properties = feature.get("properties", {})
    acquisition_date = str(feature_properties.get("startTime", ""))[:10]
    if not acquisition_date:
        parser.error("the retained catalog feature has no acquisition date")
    collection = str(feature_properties.get("collectionName", "")).upper()
    collection_maturity = {
        "NISAR_L2_GCOV_BETA_V1": "BETA",
        "NISAR_L2_GCOV_PROVISIONAL_V1": "PROVISIONAL",
        "NISAR_L2_GCOV_V1": "VALIDATED",
    }.get(collection)
    query_maturity = catalog_query.get("data_maturity") or catalog_query.get("maturity")
    if query_maturity not in {None, "BETA", "PROVISIONAL", "VALIDATED"}:
        parser.error("retained catalog has an unsupported data maturity")
    if query_maturity and collection_maturity and query_maturity != collection_maturity:
        parser.error("retained catalog maturity conflicts with the feature collection")
    maturity = query_maturity or collection_maturity
    if maturity not in {"BETA", "PROVISIONAL", "VALIDATED"}:
        parser.error("catalog maturity cannot be established from retained source metadata")
    catalog_record = {
        "schema_version": 1,
        "queried_at_utc": (
            retained_catalog.get("retrieved_at_utc")
            or retained_catalog.get("queried_at_utc")
        ),
        "source": {
            "provider": retained_catalog.get("provider") or catalog_source.get("provider"),
            "catalog_only": True,
            "pixels_downloaded": False,
            "returned_feature_count": 1,
            "potentially_truncated": False,
        },
        "query": {
            "dataset": "NISAR",
            "processing_level": "GCOV",
            "data_maturity": maturity,
            "longitude": (bounds[0] + bounds[2]) / 2,
            "latitude": (bounds[1] + bounds[3]) / 2,
            "bounds_wgs84": bounds,
            "start_date": acquisition_date,
            "end_date": acquisition_date,
        },
        "feature_count": 1,
        "features": [feature],
        "metadata_candidate_pairs": [],
        "interpretation_limit": retained_catalog.get(
            "interpretation_limit",
            "Catalog metadata identifies a candidate observation; it does not establish pixel validity or a scientific finding.",
        ),
    }

    port = get_free_port()
    import subprocess

    service = subprocess.Popen(
        [find_geckodriver(args.geckodriver), "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    driver = WebDriver(f"http://127.0.0.1:{port}")
    session_id: str | None = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                driver.request("/status")
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("geckodriver did not become ready")
        created = driver.request(
            "/session",
            method="POST",
            payload={
                "capabilities": {
                    "alwaysMatch": {
                        "browserName": "firefox",
                        "moz:firefoxOptions": {
                            "args": ["-headless", "-width=1440", "-height=1000"],
                            "prefs": {
                                "toolkit.telemetry.enabled": False,
                                "datareporting.healthreport.uploadEnabled": False,
                                "app.shield.optoutstudies.enabled": False,
                            },
                        },
                    }
                }
            },
        )
        session_id = created["value"]["sessionId"]
        driver.request(f"/session/{session_id}/url", method="POST", payload={"url": args.url})
        wait_for(
            driver,
            session_id,
            'return document.readyState==="complete"&&!!document.querySelector("#searchCatalog")'
            '&&document.querySelector("#footprintMap").innerHTML.length>500',
            45,
        )
        driver.request(
            f"/session/{session_id}/execute/sync",
            method="POST",
            payload={
                "script": (
                    'window.__echoFixtureHits=[];window.__echoPageErrors=[];'
                    'window.addEventListener("error",e=>window.__echoPageErrors.push(e.message));'
                    'const original=fetch.bind(window);window.fetch=async(input,init={})=>{'
                    'const url=String(input),method=(init.method||"GET").toUpperCase();'
                    'if(method==="POST"&&url.includes("/api/catalog")){'
                    'window.__echoFixtureHits.push("catalog");return new Response(JSON.stringify(arguments[0]),'
                    '{status:200,headers:{"Content-Type":"application/json"}})}'
                    'if(method==="POST"&&url.includes("/api/gcov-preview")){'
                    'window.__echoFixtureHits.push("preview");'
                    'if(window.__echoPreviewFailure)return new Response(JSON.stringify({error:'
                    '"GCOV scale_factor=2.0 requires packed-sample decoding; this preview supports only unscaled source samples"}),'
                    '{status:422,headers:{"Content-Type":"application/json"}});'
                    'return new Response(JSON.stringify(arguments[1]),'
                    '{status:200,headers:{"Content-Type":"application/json"}})}'
                    'return original(input,init)};return true'
                ),
                "args": [catalog_record, preview],
            },
        )
        driver.click(session_id, "#searchCatalog")
        wait_for(driver, session_id, 'return document.querySelector("#catalogDialog").open')
        for selector, value in (
            ("#queryLongitude", catalog_record["query"]["longitude"]),
            ("#queryLatitude", catalog_record["query"]["latitude"]),
            ("#queryStart", acquisition_date),
            ("#queryEnd", acquisition_date),
            ("#queryMaturity", maturity),
        ):
            set_value(driver, session_id, selector, value)
        has_bounds = driver.execute(
            session_id, 'return !!document.querySelector("#queryAreaBound0")'
        )
        if not has_bounds:
            driver.click(session_id, "#enterAreaBounds")
        for index, value in enumerate(bounds):
            set_value(driver, session_id, f"#queryAreaBound{index}", value)
        driver.click(session_id, "#applySearchArea")
        driver.click(session_id, "#runCatalogSearch")
        wait_for(
            driver,
            session_id,
            f'return !!document.querySelector(\'#timelineTrack button[data-scene-id="{scene_id}"]\')',
            40,
        )
        driver.click(session_id, f'#timelineTrack button[data-scene-id="{scene_id}"]')
        wait_for(
            driver,
            session_id,
            'return !!document.querySelector("#loadGcovPreview")'
            '&&!document.querySelector("#loadGcovPreview").disabled',
        )
        driver.click(session_id, "#loadGcovPreview")
        wait_for(
            driver,
            session_id,
            'return window.__echoFixtureHits.includes("preview")'
            '&&!document.querySelector("#previewInspector").hidden',
            40,
        )
        driver.click(session_id, "#previewRecordButton")
        wait_for(
            driver,
            session_id,
            'return document.querySelector("#recordDialog").open'
            '&&document.querySelector("#recordJson").textContent.length>0',
        )
        inspected_record = driver.execute(
            session_id,
            'const record=JSON.parse(document.querySelector("#recordJson").textContent);'
            'return {scene_id:record.source?.scene_id,qa:record.source?.provider_qa_status,'
            'value_handling:record.measurement?.value_handling,'
            'attributes:record.measurement?.source_dataset_attributes,'
            'attributes_sha256:record.measurement?.source_dataset_attributes_sha256,'
            'quality_attributes:record.measurement?.quality?.source_layer_attributes,'
            'quality_attributes_sha256:record.measurement?.quality?.source_layer_attributes_sha256,'
            'inspector_text:document.querySelector("#previewInspector").innerText}',
        )
        driver.execute(
            session_id,
            'document.querySelector("#recordDialog").close();return true',
        )
        wait_for(
            driver,
            session_id,
            'return !document.querySelector("#recordDialog").open',
        )
        preview_hits_before_reuse = driver.execute(
            session_id,
            'return window.__echoFixtureHits.filter(hit=>hit==="preview").length',
        )
        driver.click(session_id, "#loadGcovPreview")
        wait_for(
            driver,
            session_id,
            'return document.querySelectorAll("#footprintMap image.gcov-raster-preview").length===0'
            '&&document.querySelector("#loadGcovPreview").textContent.includes("LOAD BACKSCATTER")',
        )
        driver.click(session_id, "#loadGcovPreview")
        wait_for(
            driver,
            session_id,
            'return document.querySelectorAll("#footprintMap image.gcov-raster-preview").length===1'
            '&&document.querySelector("#toast").textContent.includes("QA was not refreshed")',
        )
        session_reuse = driver.execute(
            session_id,
            'return {preview_hits:window.__echoFixtureHits.filter(hit=>hit==="preview").length,'
            'toast:document.querySelector("#toast").textContent}',
        )
        cache_guards = driver.execute(
            session_id,
            'const record=JSON.parse(document.querySelector("#recordJson").textContent);'
            'const source=record.source,selection=record.access.geographic_selection;'
            'const key=gcovPreviewRequestKey(source.scene_id,source.product_url,'
            'selection.bounds_wgs84,record.measurement.frequency,record.measurement.layer);'
            'const same=key===gcovPreviewRequestKey(source.scene_id,source.product_url,'
            'selection.bounds_wgs84,record.measurement.frequency,record.measurement.layer);'
            'const area=[...selection.bounds_wgs84];area[0]-=0.001;'
            'const changedArea=key!==gcovPreviewRequestKey(source.scene_id,source.product_url,'
            'area,record.measurement.frequency,record.measurement.layer);'
            'const changedLayer=key!==gcovPreviewRequestKey(source.scene_id,source.product_url,'
            'selection.bounds_wgs84,record.measurement.frequency,"HVHV");'
            'const accepted=rememberGcovPreview("oversized",{grid:{window:{shape:[129,128]}}});'
            'return {same,changedArea,changedLayer,oversizedRejected:accepted===false}',
        )
        state = driver.execute(
            session_id,
            'return {raster:document.querySelectorAll("#footprintMap image.gcov-raster-preview").length,'
            'attribution:document.querySelector("#mapDataAttribution").textContent,'
            'inspector:document.querySelector("#previewInspector").innerText,'
            'bounds:document.querySelector(".aoi-selection")!==null,'
            'hits:window.__echoFixtureHits,errors:window.__echoPageErrors,'
            'rect:document.querySelector("#footprintMap").getBoundingClientRect().toJSON()}',
        )
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            args.screenshot.write_bytes(
                base64.b64decode(driver.request(f"/session/{session_id}/screenshot")["value"])
            )
        rect = state["rect"]
        driver.request(
            f"/session/{session_id}/actions",
            method="POST",
            payload={
                "actions": [
                    {
                        "type": "pointer",
                        "id": "mouse",
                        "parameters": {"pointerType": "mouse"},
                        "actions": [
                            {
                                "type": "pointerMove",
                                "duration": 0,
                                "x": int(rect["x"] + rect["width"] * 0.52),
                                "y": int(rect["y"] + rect["height"] * 0.5),
                            },
                            {"type": "pointerDown", "button": 0},
                            {"type": "pointerUp", "button": 0},
                        ],
                    }
                ]
            },
        )
        time.sleep(0.2)
        result = driver.execute(
            session_id,
            'return {raster:document.querySelectorAll("#footprintMap image.gcov-raster-preview").length,'
            'attribution:document.querySelector("#mapDataAttribution").textContent,'
            'inspector:document.querySelector("#previewInspector").innerText,'
            'hits:window.__echoFixtureHits,errors:window.__echoPageErrors}',
        )
        checks = {
            "raster_rendered": result["raster"] == 1,
            "area_bounds_rendered": state["bounds"],
            "qa_fail_visible_on_map": "PROVIDER QA FAIL" in result["attribution"],
            "diagnostic_disposition_visible": "QA-HELD DIAGNOSTIC PREVIEW" in result["inspector"],
            "real_pixel_inspection": "Selected pixel" in result["inspector"],
            "source_record_inspection": inspected_record["scene_id"] == scene_id,
            "only_local_replay_responses": result["hits"] == ["catalog", "preview"],
            "same_request_reuses_session_preview": (
                preview_hits_before_reuse == 1
                and session_reuse["preview_hits"] == 1
                and "QA was not refreshed" in session_reuse["toast"]
            ),
            "cache_key_binds_exact_area_and_layer": (
                cache_guards["same"]
                and cache_guards["changedArea"]
                and cache_guards["changedLayer"]
            ),
            "oversized_preview_not_retained": cache_guards["oversizedRejected"],
            "no_browser_errors": not result["errors"],
        }
        measurement_attributes_hash_valid = (
            isinstance(inspected_record["attributes"], dict)
            and inspected_record["attributes_sha256"]
            == canonical_json_sha256(inspected_record["attributes"])
        )
        quality_attributes_hash_valid = (
            isinstance(inspected_record["quality_attributes"], dict)
            and inspected_record["quality_attributes_sha256"]
            == canonical_json_sha256(inspected_record["quality_attributes"])
        )
        attributes_present = (
            measurement_attributes_hash_valid
            and quality_attributes_hash_valid
            and isinstance(inspected_record["value_handling"], str)
        )
        if args.require_source_attributes:
            checks["hashed_source_attributes_inspected"] = attributes_present
            handling = inspected_record["value_handling"]
            inspector_text = inspected_record["inspector_text"]
            checks["sample_handling_visible"] = (
                isinstance(handling, str)
                and isinstance(inspector_text, str)
                and handling in inspector_text
            )
        driver.click(session_id, f'#timelineTrack button[data-scene-id="{scene_id}"]')
        driver.execute(
            session_id,
            'window.__echoPreviewFailure=true;const layer=document.querySelector("#previewLayer");'
            'if(![...layer.options].some(option=>option.value==="HVHV"))throw new Error("HVHV is not selectable for the retained scene");'
            'layer.value="HVHV";layer.dispatchEvent(new Event("change",{bubbles:true}));return true',
        )
        failure_path_ready = driver.execute(
            session_id,
            'const button=document.querySelector("#loadGcovPreview");'
            'return {disabled:button.disabled,hidden:button.hidden,text:button.textContent,'
            'selected:document.querySelector(".timeline-observation.selected")?.dataset.sceneId,'
            'area:document.querySelector(".aoi-selection")!==null};',
        )
        if failure_path_ready["disabled"] or failure_path_ready["hidden"]:
            raise RuntimeError(
                f"Unsupported-encoding failure test setup is not actionable: {failure_path_ready}"
            )
        driver.click(session_id, "#loadGcovPreview")
        encoding_error_probe = (
            'const status=document.querySelector("#gcovReadStatus");'
            'return {state:status?.dataset.state,text:status?.textContent,visible:!status?.hidden,'
            'raster:document.querySelectorAll("#footprintMap image.gcov-raster-preview").length,'
            'inspector:document.querySelector("#previewInspector").innerText,'
            'hits:window.__echoFixtureHits,errors:window.__echoPageErrors,'
            'button:document.querySelector("#loadGcovPreview").textContent};'
        )
        try:
            encoding_error_state = wait_for(
                driver,
                session_id,
                'const status=document.querySelector("#gcovReadStatus");'
                'return status?.dataset.state==="error"?{state:status.dataset.state,'
                'text:status.textContent,visible:!status.hidden,'
                'raster:document.querySelectorAll("#footprintMap image.gcov-raster-preview").length,'
                'inspector:document.querySelector("#previewInspector").innerText,'
                'errors:window.__echoPageErrors}:false',
            )
        except TimeoutError as exc:
            debug_state = driver.execute(session_id, encoding_error_probe)
            raise RuntimeError(
                f"Unsupported-encoding browser path did not reach error state: {debug_state}"
            ) from exc
        checks["unsupported_encoding_error_is_visible_without_stale_raster"] = (
            encoding_error_state["visible"]
            and "scale_factor=2.0" in encoding_error_state["text"]
            and "No preview was loaded" in encoding_error_state["text"]
            and encoding_error_state["raster"] == 0
            and not encoding_error_state["inspector"]
            and not encoding_error_state["errors"]
        )
        print(
            json.dumps(
                {
                    "status": "PASS" if all(checks.values()) else "FAIL",
                    "scene_id": scene_id,
                    "checks": checks,
                    "map_attribution": result["attribution"],
                    "pixel_readout": next(
                        (line for line in result["inspector"].splitlines() if "Selected pixel" in line),
                        None,
                    ),
                    "source_metadata_status": (
                        "PRESENT_AND_HASHED" if attributes_present
                        else "NOT_RECORDED_IN_RETAINED_PREVIEW"
                    ),
                    "measurement_attributes_hash_valid": measurement_attributes_hash_valid,
                    "quality_attributes_hash_valid": quality_attributes_hash_valid,
                    "measurement_attributes_sha256": inspected_record["attributes_sha256"],
                    "quality_attributes_sha256": inspected_record["quality_attributes_sha256"],
                    "measurement_value_handling": inspected_record["value_handling"],
                    "unsupported_encoding_error_state": encoding_error_state,
                    "session_preview_reuse": session_reuse,
                    "session_cache_guards": cache_guards,
                    "browser_errors": result["errors"],
                    "screenshot": str(args.screenshot) if args.screenshot else None,
                },
                indent=2,
            )
        )
        return 0 if all(checks.values()) else 1
    finally:
        if session_id:
            try:
                driver.request(f"/session/{session_id}", method="DELETE")
            except Exception:
                pass
        service.terminate()
        try:
            service.wait(timeout=3)
        except subprocess.TimeoutExpired:
            service.kill()
            service.wait()


if __name__ == "__main__":
    raise SystemExit(main())
