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
            '&& document.querySelector("#footprintMap").innerHTML.length > 500',
        )
        if not page_ready:
            raise AssertionError("ECHO map did not finish rendering")
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
            'layer.value = "OFF"; layer.dispatchEvent(new Event("change", {bubbles:true})); return true',
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
                    "keyboard_wgs84_bounds_wsen": keyboard_bounds,
                    "escape_preserved_selection": True,
                    "point_fields_disabled_for_area": point_fields_disabled,
                    "global_pointer_wgs84_bounds_wsen": pointer_bounds,
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
