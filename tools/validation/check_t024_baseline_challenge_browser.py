#!/usr/bin/env python3
"""Verify T024's retained temporal baseline challenge-to-map workflow locally.

This check uses an already-running loopback ECHO workbench. It reads the
retained diagnostic assessment and series through the application, submits no
provider requests, and creates or modifies no investigation records.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import subprocess
import time
import urllib.parse
from typing import Any

from check_map_area_browser import WebDriver, find_geckodriver, get_free_port


CASE_ID = "rio-grande-do-sul-cross-sensor-diagnostic-2024"
HYPOTHESIS_ID = "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"
SERIES_SHA256 = "191cac49a1718c3b5c0fd85d2c7ee814c37c484e8ba7462e92aa9cd2c1bae738"
BEFORE_UTC = "2024-05-11T08:49:47+00:00"
AFTER_UTC = "2025-06-23T08:49:37+00:00"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=f"http://127.0.0.1:8766/?case_id={CASE_ID}",
        help="loopback URL for the interactive ECHO workbench",
    )
    parser.add_argument("--geckodriver", help="geckodriver executable path")
    args = parser.parse_args()

    target = urllib.parse.urlsplit(args.url)
    host = target.hostname or ""
    try:
        loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    query = urllib.parse.parse_qs(target.query)
    if (
        target.scheme != "http"
        or not loopback
        or target.username
        or target.password
        or query.get("case_id") != [CASE_ID]
    ):
        parser.error(f"--url must be loopback HTTP and select case_id={CASE_ID}")

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
            except OSError:
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
                        "moz:firefoxOptions": {
                            "args": ["-headless", "-width=1366", "-height=900"]
                        },
                    }
                }
            },
        )
        session_id = created["value"]["sessionId"]
        browser.request(
            f"/session/{session_id}/url", method="POST", payload={"url": args.url}
        )
        browser.wait_for(
            session_id,
            'return document.readyState === "complete" '
            f'&& document.querySelector("#caseSelector")?.value === "{CASE_ID}" '
            '&& document.querySelector("#openCaseInvestigation")?.hidden === false '
            '&& document.querySelector("#footprintMap").innerHTML.length > 500',
            timeout_seconds=30,
        )
        browser.click(session_id, "#openCaseInvestigation")
        hypothesis_selector = (
            f'.challenge-hypothesis[data-hypothesis-id="{HYPOTHESIS_ID}"]'
        )
        browser.wait_for(
            session_id,
            'return document.querySelector("#investigationDialog").open '
            f'&& document.querySelector({json.dumps(hypothesis_selector)})',
            timeout_seconds=20,
        )
        browser.execute(
            session_id,
            'window.__echoApiCalls=[];window.__echoPageErrors=[];'
            'window.addEventListener("error",event=>window.__echoPageErrors.push(event.message));'
            'const originalFetch=window.fetch.bind(window);'
            'window.fetch=(input,init={})=>{if(String(input).includes("/api/"))'
            'window.__echoApiCalls.push({url:String(input),method:(init.method||"GET").toUpperCase()});'
            'return originalFetch(input,init)};return true',
        )
        browser.click(session_id, hypothesis_selector)
        browser.wait_for(
            session_id,
            'return document.querySelector("#adversarialChallengeDialog").open '
            '&& document.querySelector("#adversarialChallengeContent [data-show-temporal-series]")',
            timeout_seconds=30,
        )

        # Sensitivity content is intentionally progressive: open its disclosure.
        browser.execute(
            session_id,
            'const details=[...document.querySelectorAll("#adversarialChallengeContent details")]'
            '.find(item=>item.querySelector(".challenge-temporal-baseline"));'
            'if(!details)throw new Error("temporal baseline disclosure is missing");'
            'details.open=true;return true',
        )
        temporal = browser.execute(
            session_id,
            'return document.querySelector("#adversarialChallengeContent '
            '.challenge-temporal-baseline").innerText',
        )
        required_text = (
            "TEMPORAL BASELINE CHECK · DIAGNOSTIC",
            "1034 of 1199 AOI cells marked valid by every acquisition's retained product mask",
            "24.0 d",
            "384.0 d",
            "408.0 d",
            "-1.252 dB",
        )
        missing = [item for item in required_text if item not in temporal]
        if missing:
            raise AssertionError(
                f"temporal challenge omitted expected record values: {missing}"
            )
        if "validated all-date support" in temporal:
            raise AssertionError("temporal mask support was labeled as provider validation")

        map_button_selector = (
            '#adversarialChallengeContent '
            '[data-show-temporal-series][data-comparison-key="baseline:0"]'
        )
        handoff = browser.execute(
            session_id,
            f"const button=document.querySelector({json.dumps(map_button_selector)});"
            'return button?{comparison_key:button.dataset.comparisonKey,'
            'before_utc:button.dataset.beforeUtc,after_utc:button.dataset.afterUtc,'
            'series_sha256:button.dataset.seriesSha256}:null',
        )
        expected_handoff = {
            "comparison_key": "baseline:0",
            "before_utc": BEFORE_UTC,
            "after_utc": AFTER_UTC,
            "series_sha256": SERIES_SHA256,
        }
        if handoff != expected_handoff:
            raise AssertionError(
                f"challenge handoff does not match retained series: {handoff}"
            )

        browser.click(session_id, map_button_selector)
        browser.wait_for(
            session_id,
            'return !document.querySelector("#adversarialChallengeDialog").open '
            '&& !document.querySelector("#operaTemporalSeriesInspector").hidden '
            '&& document.querySelector("#operaTemporalSeriesInspector").innerText'
            '.includes("FIRST-ACQUISITION BASELINE")',
            timeout_seconds=20,
        )
        result: dict[str, Any] = browser.execute(
            session_id,
            'return {comparison:document.querySelector("#operaTemporalSeriesInspector").innerText,'
            'map_attribution:document.querySelector("#mapDataAttribution").textContent,'
            'api_calls:window.__echoApiCalls,page_errors:window.__echoPageErrors}',
        )
        comparison = result["comparison"].lower()
        attribution = result["map_attribution"]
        if "no consolidated pass/fail" not in comparison or "diagnostic only" not in comparison:
            raise AssertionError(
                "map inspector did not retain the unresolved provider-QA boundary"
            )
        if "FIRST-ACQUISITION BASELINE" not in attribution or "DIAGNOSTIC ONLY" not in attribution:
            raise AssertionError("map attribution omitted baseline or diagnostic status")
        if len(result["api_calls"]) != 1 or result["api_calls"][0]["method"] != "GET":
            raise AssertionError(f"unexpected API activity during challenge: {result['api_calls']}")
        if result["page_errors"]:
            raise AssertionError(f"browser reported page errors: {result['page_errors']}")

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "case_id": CASE_ID,
                    "hypothesis_id": HYPOTHESIS_ID,
                    "temporal_sensitivity": {
                        "selected_shared_support": "1034/1199",
                        "baseline_median_db": "-1.252",
                        "baseline_interval_days": 408.0,
                        "series_sha256": SERIES_SHA256,
                    },
                    "map_handoff": handoff,
                    "qa_boundary_preserved": True,
                    "api_calls": result["api_calls"],
                    "page_errors": result["page_errors"],
                    "scientific_limit": (
                        "Sentinel-1-derived OPERA RTC-S1 remains diagnostic; "
                        "no causal interpretation or validated event result is established."
                    ),
                },
                indent=2,
            )
        )
        return 0
    finally:
        if session_id:
            try:
                browser.request(f"/session/{session_id}", method="DELETE")
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
