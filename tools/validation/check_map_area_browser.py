#!/usr/bin/env python3
"""Exercise ECHO's map-to-catalog AOI flow in local Firefox via W3C WebDriver.

This check uses only a local ECHO workbench. It does not submit catalog or
provider requests and does not create or modify investigation records.
"""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_URL = "http://127.0.0.1:8766/?case_id=iraq-2026-nisar-gcov-diagnostic"
W3C_ELEMENT_ID = "element-6066-11e4-a52e-4f735466cecf"


class WebDriver:
    def __init__(self, base_url: str, timeout_seconds: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(
        self, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"WebDriver {method} {path}: HTTP {error.code}: {detail}") from error

    def execute(self, session_id: str, script: str) -> Any:
        return self.request(
            f"/session/{session_id}/execute/sync",
            method="POST",
            payload={"script": script, "args": []},
        )["value"]

    def click(self, session_id: str, selector: str) -> None:
        self.request(
            f"/session/{session_id}/execute/sync",
            method="POST",
            payload={
                "script": (
                    f"const element=document.querySelector({json.dumps(selector)});"
                    'if(element)element.scrollIntoView({block:"center",inline:"nearest"});'
                    "return Boolean(element)"
                ),
                "args": [],
            },
        )
        element = self.request(
            f"/session/{session_id}/element",
            method="POST",
            payload={"using": "css selector", "value": selector},
        )["value"][W3C_ELEMENT_ID]
        self.request(f"/session/{session_id}/element/{element}/click", method="POST", payload={})

    def key(self, session_id: str, key_code: int, *, shift: bool = False) -> None:
        actions = []
        if shift:
            actions.append({"type": "keyDown", "value": chr(0xE008)})
        key_value = chr(key_code)
        actions.extend(
            [{"type": "keyDown", "value": key_value}, {"type": "keyUp", "value": key_value}]
        )
        if shift:
            actions.append({"type": "keyUp", "value": chr(0xE008)})
        self.request(
            f"/session/{session_id}/actions",
            method="POST",
            payload={"actions": [{"type": "key", "id": "keyboard", "actions": actions}]},
        )
        time.sleep(0.12)

    def wait_for(self, session_id: str, script: str, *, timeout_seconds: float = 20) -> Any:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            result = self.execute(session_id, script)
            if result:
                return result
            time.sleep(0.1)
        raise TimeoutError(f"Timed out waiting for browser condition: {script}")


def find_geckodriver(explicit_path: str | None) -> str:
    candidates = [explicit_path, shutil.which("geckodriver"), "/snap/bin/geckodriver"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("geckodriver was not found; pass --geckodriver PATH")


def get_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def read_bounds(driver: WebDriver, session_id: str) -> list[str]:
    return driver.execute(
        session_id,
        'return [0,1,2,3].map(i => document.querySelector("#queryAreaBound" + i).value)',
    )


def assert_rectangle(bounds: list[str]) -> None:
    west, south, east, north = map(float, bounds)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise AssertionError(f"WGS84 bounds are invalid or unordered: {bounds}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="local interactive ECHO page URL")
    parser.add_argument("--geckodriver", help="geckodriver executable path")
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="optional path for the selected-area dialog screenshot",
    )
    args = parser.parse_args()

    target = urllib.parse.urlsplit(args.url)
    host = target.hostname or ""
    try:
        loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    if target.scheme != "http" or not loopback or target.username or target.password:
        parser.error("--url must be an HTTP loopback address for the local ECHO workbench")

    driver_path = find_geckodriver(args.geckodriver)
    port = get_free_port()
    service = subprocess.Popen(
        [driver_path, "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    browser = WebDriver(f"http://127.0.0.1:{port}")
    session_id: str | None = None
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                browser.request("/status")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        else:
            raise RuntimeError("geckodriver did not become ready")
        created = browser.request(
            "/session",
            method="POST",
            payload={
                "capabilities": {
                    "alwaysMatch": {
                        "browserName": "firefox",
                        "moz:firefoxOptions": {"args": ["-headless", "-width=1366", "-height=900"]},
                    }
                }
            },
        )
        session_id = created["value"]["sessionId"]
        browser.request(f"/session/{session_id}/url", method="POST", payload={"url": args.url})
        page_ready = browser.wait_for(
            session_id,
            'return document.readyState === "complete" '
            '&& !!document.querySelector("#drawArea") '
            '&& document.querySelector("#footprintMap").innerHTML.length > 500 '
            '&& document.querySelector("#caseSelector option")?.textContent !== "Loading available cases…"',
        )
        if not page_ready:
            raise AssertionError("ECHO map did not finish rendering")
        satellite_pan_retention: dict[str, Any] = {
            "status": "NOT_RUN",
            "reason": "An explicit case URL skips the first-use global map-pan check.",
        }
        startup_url = urllib.parse.urlsplit(args.url)
        if "case_id" not in urllib.parse.parse_qs(startup_url.query):
            home_ready = browser.wait_for(
                session_id,
                'return document.querySelector("#caseSelector").value !== "" '
                '&& !document.querySelector("#timelinePanel").hidden '
                '&& !document.querySelector("#evidencePanel").hidden;',
            )
            if not home_ready:
                raise AssertionError("default route did not open the retained worked case")
            exploration_home = browser.execute(
                session_id,
                'const selector=document.querySelector("#caseSelector");'
                'return {active:document.body.classList.contains("retained-case-view"),'
                'url:location.pathname+location.search,heading:document.querySelector(".case-heading h1").textContent,'
                'selectorLabel:document.querySelector("#caseSelectorLabel").textContent,'
                'selectedCase:selector.value,globalOption:[...selector.options].some(option=>option.value===""&&option.textContent.includes("GLOBAL EXPLORATION")),'
                'timelineHidden:document.querySelector("#timelinePanel").hidden,'
                'evidenceHidden:document.querySelector("#evidencePanel").hidden,'
                'browseDate:new URL(document.querySelector(".gibs-basemap")?.getAttribute("href")||location.href).searchParams.get("TIME"),'
                'apiReads:performance.getEntriesByType("resource").map(item=>new URL(item.name).pathname).filter(path=>path.startsWith("/api/"))};',
            )
            if not (
                exploration_home["active"]
                and exploration_home["selectedCase"]
                and exploration_home["globalOption"]
                and exploration_home["selectorLabel"] == "SAVED CASES"
                and not exploration_home["timelineHidden"]
                and not exploration_home["evidenceHidden"]
                and exploration_home["browseDate"]
                and "/api/case" in exploration_home["apiReads"]
            ):
                raise AssertionError(f"retained worked-case startup state is inconsistent: {exploration_home}")
            browser.execute(
                session_id,
                'const selector=document.querySelector("#caseSelector"); selector.value=""; '
                'selector.dispatchEvent(new Event("change",{bubbles:true})); return true;',
            )
            global_workspace_ready = browser.wait_for(
                session_id,
                'return location.search === "?mode=explore" '
                '&& document.body.classList.contains("exploration-start") '
                '&& !document.querySelector("#mapImageryLayer").disabled '
                '&& document.querySelector(".gibs-basemap")?.getAttribute("href")?.includes("BlueMarble_NextGeneration") '
                '&& ["#loadGcovPreview","#openOpera","#openBhoonidhi","#openDswxContext"].every(id=>document.querySelector(id).hidden);',
            )
            global_workspace = browser.execute(
                session_id,
                'return {url:location.pathname+location.search,heading:document.querySelector(".case-heading h1").textContent,'
                'contextDate:document.querySelector("#mapDataAttribution").textContent,'
                'hidden:["#loadGcovPreview","#openOpera","#openBhoonidhi","#openDswxContext"].map(id=>document.querySelector(id).hidden),'
                'imageryDisabled:document.querySelector("#mapImageryLayer").disabled,'
                'satelliteSource:document.querySelector(".gibs-basemap")?.getAttribute("href"),'
                'satelliteMode:document.querySelector("#mapImageryLayer").value,'
                'coordinateReadout:document.querySelector(".coordinate-readout").innerText,'
                'searchMarkerVisible:!!document.querySelector("#footprintMap .search-ring")};',
            )
            if not global_workspace_ready or not all(global_workspace["hidden"]) or global_workspace["imageryDisabled"] or global_workspace["satelliteMode"] != "BLUE_MARBLE" or global_workspace["searchMarkerVisible"] or "GLOBAL OVERVIEW" not in global_workspace["coordinateReadout"]:
                raise AssertionError(f"first-use global exploration controls are inconsistent: {global_workspace}")
            browser.wait_for(
                session_id,
                'return performance.getEntriesByType("resource").some(item=>'
                'item.name.includes("BlueMarble_NextGeneration")&&item.responseEnd>0);',
                timeout_seconds=15,
            )
            browser.click(session_id, "#zoomIn")
            browser.click(session_id, "#zoomIn")
            map_rect = browser.execute(
                session_id,
                'return document.querySelector("#footprintMap").getBoundingClientRect().toJSON()',
            )
            pan_x = round(map_rect["left"] + map_rect["width"] * 0.50)
            pan_y = round(map_rect["top"] + map_rect["height"] * 0.50)
            browser.request(
                f"/session/{session_id}/actions",
                method="POST",
                payload={
                    "actions": [{
                        "type": "pointer", "id": "satellite-pan",
                        "parameters": {"pointerType": "mouse"},
                        "actions": [
                            {"type": "pointerMove", "origin": "viewport", "x": pan_x, "y": pan_y},
                            {"type": "pointerDown", "button": 0},
                            {"type": "pointerMove", "origin": "viewport", "x": pan_x + 45, "y": pan_y + 25, "duration": 250},
                            {"type": "pointerUp", "button": 0},
                        ],
                    }],
                },
            )
            satellite_pan_retention = browser.execute(
                session_id,
                'const map=document.querySelector("#footprintMap");'
                'const current=map.querySelector(".gibs-basemap:not(.gibs-basemap-stale)");'
                'const url=current?.getAttribute("href");'
                'const response=performance.getEntriesByType("resource").some(item=>item.name===url&&item.responseEnd>0);'
                'return {current:url,staleVisible:!!map.querySelector(".gibs-basemap-stale"),'
                'currentImageAlreadyLoaded:response,anySatelliteImageVisible:!!map.querySelector(".gibs-basemap")};',
            )
            if not satellite_pan_retention["anySatelliteImageVisible"] or not (
                satellite_pan_retention["staleVisible"] or satellite_pan_retention["currentImageAlreadyLoaded"]
            ):
                raise AssertionError(f"satellite context disappeared during map pan: {satellite_pan_retention}")
            browser.request(f"/session/{session_id}/url", method="POST", payload={"url": args.url})
            browser.wait_for(
                session_id,
                'return document.body.classList.contains("retained-case-view") '
                '&& document.querySelector(".gibs-basemap")?.getAttribute("href")?.includes("TIME=");',
            )
        else:
            exploration_home = None
        bhoonidhi_visible = browser.execute(
            session_id,
            'const button=document.querySelector("#openBhoonidhi"); '
            'return !button.hidden && getComputedStyle(button).display !== "none";',
        )
        if bhoonidhi_visible:
            browser.execute(
                session_id,
                'window.__bhoonidhiRequests = 0; const originalFetch = window.fetch.bind(window); '
                'window.fetch = (...args) => { if (String(args[0]).includes("bhoonidhi")) window.__bhoonidhiRequests++; '
                'return originalFetch(...args); };',
            )
            browser.click(session_id, "#openBhoonidhi")
            account_notice_visible = browser.wait_for(
                session_id,
                'const dialog=document.querySelector("#bhoonidhiDialog"); '
                'return dialog.open && dialog.textContent.includes("optional search needs a registered Bhoonidhi account") '
                '&& dialog.textContent.includes("Close this dialog to continue with ECHO") '
                '&& !document.querySelector("#bhoonidhiUserId").value '
                '&& !document.querySelector("#bhoonidhiPassword").value;',
            )
            browser.click(session_id, "#closeBhoonidhiDialog")
            guest_workspace_available = browser.wait_for(
                session_id,
                'return !document.querySelector("#bhoonidhiDialog").open '
                '&& !!document.querySelector("#caseSelector") '
                '&& document.querySelector("#footprintMap").innerHTML.length > 500 '
                '&& window.__bhoonidhiRequests === 0;',
            )
            if not guest_workspace_available:
                raise AssertionError("optional Bhoonidhi dialog did not close cleanly without credentials")
            optional_provider_flow = {
                "visible_in_current_case": True,
                "account_notice_visible_with_empty_fields": bool(account_notice_visible),
                "closed_to_usable_workspace": bool(guest_workspace_available),
            }
        else:
            optional_provider_flow = {
                "visible_in_current_case": False,
                "hidden_as_unrelated_to_selected_case": True,
            }
        gesture_check = browser.execute(
            session_id,
            'const map = document.querySelector("#footprintMap"); '
            'const bounds = map.getBoundingClientRect(); '
            'const x = Math.round(bounds.left + bounds.width * 0.68), y = Math.round(bounds.top + bounds.height * 0.37); '
            'const value = (label) => Number(label.dataset.coordinate); '
            'const coordinateAt = (clientX,clientY) => { const labels = [...map.querySelectorAll(".grid-label")]; '
            'const point = map.createSVGPoint(); point.x = clientX; point.y = clientY; '
            'const local = point.matrixTransform(map.getScreenCTM().inverse()); '
            'const interpolate = (axis,entries,position) => { const first=entries[0],last=entries.at(-1); '
            'const labelOffset=axis==="y"?3:0,low=Number(first.getAttribute(axis))-labelOffset,high=Number(last.getAttribute(axis))-labelOffset; '
            'return value(first)+(position-low)/(high-low)*(value(last)-value(first)); }; '
            'return [interpolate("x",labels.filter((label)=>label.dataset.axis==="longitude"),local.x), '
            'interpolate("y",labels.filter((label)=>label.dataset.axis==="latitude"),local.y)]; }; '
            'const span = () => { const labels=[...map.querySelectorAll(".grid-label")].filter((label)=>label.dataset.axis==="longitude"); '
            'return Math.abs(value(labels[0])-value(labels.at(-1))); }; '
            'const anchorBefore = coordinateAt(x,y); const zoomBefore = span(); '
            'const pinchIn = new WheelEvent("wheel", {bubbles:true, cancelable:true, ctrlKey:true, clientX:x, clientY:y, deltaY:-35}); '
            'map.dispatchEvent(pinchIn); for (let index=0; index<9; index++) map.dispatchEvent(new WheelEvent("wheel", '
            '{bubbles:true, cancelable:true, ctrlKey:true, clientX:x, clientY:y, deltaY:-35})); '
            'const zoomAfterIn = span(); const anchorAfter = coordinateAt(x,y); '
            'const pinchOut = new WheelEvent("wheel", {bubbles:true, cancelable:true, ctrlKey:true, clientX:x, clientY:y, deltaY:35}); '
            'for (let index=0; index<10; index++) map.dispatchEvent(new WheelEvent("wheel", '
            '{bubbles:true, cancelable:true, ctrlKey:true, clientX:x, clientY:y, deltaY:35})); '
            'const zoomAfterOut = span(); '
            'const normalScroll = new WheelEvent("wheel", {bubbles:true, cancelable:true, clientX:x, clientY:y, deltaY:50}); '
            'map.dispatchEvent(normalScroll); '
            'const zoomAfterScroll = span(); '
            'document.querySelector("#drawArea").click(); '
            'const drawModeBefore = map.classList.contains("area-draw-mode"); '
            'const drawModePinch = new WheelEvent("wheel", {bubbles:true, cancelable:true, ctrlKey:true, clientX:x, clientY:y, deltaY:-35}); '
            'map.dispatchEvent(drawModePinch); '
            'const drawModeAfter = map.classList.contains("area-draw-mode"); '
            'const zoomAfterDrawModePinch = span(); '
            'document.querySelector("#drawArea").click(); '
            'return {zoomBefore, zoomAfterIn, zoomAfterOut, zoomAfterScroll, zoomAfterDrawModePinch, '
            'anchorBefore, anchorAfter, pinchPrevented:pinchIn.defaultPrevented, '
            'normalScrollPrevented:normalScroll.defaultPrevented, drawModeBefore, drawModeAfter, '
            'drawPinchPrevented:drawModePinch.defaultPrevented};',
        )
        if not (
            gesture_check["zoomAfterIn"] < gesture_check["zoomBefore"]
            and gesture_check["zoomAfterOut"] > gesture_check["zoomAfterIn"]
            and gesture_check["zoomAfterScroll"] == gesture_check["zoomAfterOut"]
            and gesture_check["zoomAfterDrawModePinch"] == gesture_check["zoomAfterOut"]
            and gesture_check["pinchPrevented"]
            and not gesture_check["normalScrollPrevented"]
            and gesture_check["drawModeBefore"]
            and gesture_check["drawModeAfter"]
            and not gesture_check["drawPinchPrevented"]
            and max(
                abs(gesture_check["anchorBefore"][index] - gesture_check["anchorAfter"][index])
                for index in range(2)
            ) < 0.001
        ):
            raise AssertionError(f"pinch/scroll/AOI interaction failed: {gesture_check}")
        browser.execute(
            session_id,
            'window.__catalogPosts = 0; '
            'window.__echoFetch = window.fetch.bind(window); '
            'window.fetch = (...args) => { '
            'if (String(args[0]).includes("/api/catalog")) window.__catalogPosts++; '
            'return window.__echoFetch(...args); }; return true',
        )

        # Keyboard path: set two corners and inspect the exact catalog handoff.
        browser.click(session_id, "#drawArea")
        if browser.execute(session_id, 'return document.activeElement.id === "footprintMap"') is not True:
            raise AssertionError("area selection did not focus the map")
        for key_code in (0xE014, 0xE007, 0xE014, 0xE014, 0xE013, 0xE013, 0xE007):
            browser.key(session_id, key_code)
        browser.wait_for(
            session_id,
            'return document.querySelector("#drawArea").getAttribute("aria-pressed") === "false"',
        )
        browser.click(session_id, "#searchCatalog")
        keyboard_bounds = read_bounds(browser, session_id)
        assert_rectangle(keyboard_bounds)
        point_fields_disabled = browser.execute(
            session_id,
            'return [document.querySelector("#queryLongitude").disabled, '
            'document.querySelector("#queryLatitude").disabled]',
        )
        if point_fields_disabled != [True, True]:
            raise AssertionError("point fields remain active during an area search")
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            encoded = browser.request(f"/session/{session_id}/screenshot")["value"]
            args.screenshot.write_bytes(base64.b64decode(encoded))

        # Escape cancels replacement without discarding the previously selected AOI.
        browser.click(session_id, "#closeCatalogDialog")
        browser.click(session_id, "#drawArea")
        browser.key(session_id, 0xE014)
        browser.key(session_id, 0xE007)
        browser.key(session_id, 0xE00C)
        browser.wait_for(
            session_id,
            'return document.querySelector("#drawArea").getAttribute("aria-pressed") === "false"',
        )
        browser.click(session_id, "#searchCatalog")
        after_cancel_bounds = read_bounds(browser, session_id)
        if after_cancel_bounds != keyboard_bounds:
            raise AssertionError("Escape changed the previously selected AOI")
        browser.click(session_id, "#closeCatalogDialog")

        # Pointer path: repeat selection from global view in the western/southern hemispheres.
        browser.execute(
            session_id,
            'const layer = document.querySelector("#mapImageryLayer"); '
            'layer.value = "BLUE_MARBLE"; layer.dispatchEvent(new Event("change", {bubbles:true})); return true',
        )
        browser.click(session_id, "#worldView")
        browser.click(session_id, "#drawArea")
        rect = browser.execute(
            session_id,
            'return document.querySelector("#footprintMap").getBoundingClientRect().toJSON()',
        )
        x0, x1 = round(rect["left"] + rect["width"] * 0.30), round(rect["left"] + rect["width"] * 0.34)
        y0, y1 = round(rect["top"] + rect["height"] * 0.62), round(rect["top"] + rect["height"] * 0.66)
        browser.request(
            f"/session/{session_id}/actions",
            method="POST",
            payload={
                "actions": [
                    {
                        "type": "pointer",
                        "id": "mouse",
                        "parameters": {"pointerType": "mouse"},
                        "actions": [
                            {"type": "pointerMove", "origin": "viewport", "x": x0, "y": y0},
                            {"type": "pointerDown", "button": 0},
                            {"type": "pointerMove", "origin": "viewport", "x": x1, "y": y1, "duration": 250},
                            {"type": "pointerUp", "button": 0},
                        ],
                    }
                ]
            },
        )
        browser.click(session_id, "#searchCatalog")
        pointer_bounds = read_bounds(browser, session_id)
        assert_rectangle(pointer_bounds)
        west, south, east, north = map(float, pointer_bounds)
        if not (west < east < 0 and south < north < 0):
            raise AssertionError(
                "global pointer AOI was not in the western/southern hemispheres: "
                f"{pointer_bounds}"
            )

        catalog_posts = browser.execute(session_id, "return window.__catalogPosts")
        if catalog_posts != 0:
            raise AssertionError(f"browser unexpectedly submitted {catalog_posts} catalog request(s)")
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "url": args.url,
            "default_worked_case_home": exploration_home,
                    "keyboard_wgs84_bounds_wsen": keyboard_bounds,
                    "escape_preserved_selection": True,
                    "point_fields_disabled_for_area": point_fields_disabled,
                    "global_pointer_wgs84_bounds_wsen": pointer_bounds,
                    "optional_bhoonidhi_without_login": optional_provider_flow,
                    "satellite_context_during_pan": satellite_pan_retention,
                    "pinch_zoom_and_scroll_check": gesture_check,
                    "catalog_requests_submitted": catalog_posts,
                    "measurement_or_investigation_changes": False,
                },
                indent=2,
            )
        )
        return 0
    finally:
        if session_id:
            try:
                browser.request(f"/session/{session_id}", method="DELETE")
            except (OSError, urllib.error.URLError, RuntimeError):
                pass
        service.terminate()
        try:
            service.wait(timeout=5)
        except subprocess.TimeoutExpired:
            service.kill()
            service.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
