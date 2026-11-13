#!/usr/bin/env python3
"""Replay a retained authentic GCOV window through the local UI in Firefox.

Catalog and preview responses are served from local JSON records so the browser
check exercises the real search, timeline, raster, QA, and pixel-inspection flow
without another provider request. The ECHO server must already be running.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
from pathlib import Path
from typing import Any

from check_map_area_browser import WebDriver, find_geckodriver, get_free_port
from check_observation_challenge_browser import require_loopback_url


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_URL = "http://127.0.0.1:8766/?case_id=iraq-2026-nisar-gcov-diagnostic"
DEFAULT_PREVIEW = ROOT / "data/research/nisar-hawaii-hilo-gcov-diagnostic-preview-2026-11-10.json"
DEFAULT_CATALOG = ROOT / "data/research/validated-gcov-global-time-series-2026-11-10-13.json"
SCENE_ID = "NISAR_L2_PR_GCOV_035_072_D_078_4005_DHDH_A_20261110T045757_20261110T045815_P05036_N_P_J_001"


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
    args = parser.parse_args()
    require_loopback_url(args.url, parser)
    preview = json.loads(args.preview.read_text(encoding="utf-8"))
    retained_catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    scene_id = preview.get("source", {}).get("scene_id")
    if (
        preview.get("record_type") != "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW"
        or scene_id != SCENE_ID
        or preview.get("source", {}).get("provider_qa_status") != "FAIL"
        or preview.get("scientific_disposition") != "QA_HELD_DIAGNOSTIC_PREVIEW"
    ):
        parser.error("preview file is not the expected QA-held real Hawaii NISAR record")
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
    catalog_record = {
        "schema_version": 1,
        "queried_at_utc": retained_catalog["retrieved_at_utc"],
        "source": {
            "provider": retained_catalog["provider"],
            "catalog_only": True,
            "pixels_downloaded": False,
            "returned_feature_count": 1,
            "potentially_truncated": False,
        },
        "query": {
            "dataset": "NISAR",
            "processing_level": "GCOV",
            "data_maturity": "VALIDATED",
            "longitude": (bounds[0] + bounds[2]) / 2,
            "latitude": (bounds[1] + bounds[3]) / 2,
            "bounds_wgs84": bounds,
            "start_date": "2026-11-10",
            "end_date": "2026-11-10",
        },
        "feature_count": 1,
        "features": [feature],
        "metadata_candidate_pairs": [],
        "interpretation_limit": retained_catalog["interpretation_limit"],
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
                    'window.__echoFixtureHits.push("preview");return new Response(JSON.stringify(arguments[1]),'
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
            ("#queryStart", "2026-11-10"),
            ("#queryEnd", "2026-11-10"),
            ("#queryMaturity", "VALIDATED"),
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
            "only_local_replay_responses": result["hits"] == ["catalog", "preview"],
            "no_browser_errors": not result["errors"],
        }
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
