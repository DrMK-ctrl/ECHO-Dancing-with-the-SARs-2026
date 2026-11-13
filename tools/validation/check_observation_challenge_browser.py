#!/usr/bin/env python3
"""Verify the local Iraq observation challenge stays honest under provider QA hold.

The check uses headless Firefox against an already-running loopback ECHO
workbench. It performs one local GET for the challenge record and submits no
provider requests, draft mutations, or other writes.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import shutil
import subprocess
import time
import urllib.parse
from typing import Any

from check_map_area_browser import W3C_ELEMENT_ID, WebDriver, find_geckodriver, get_free_port


DEFAULT_URL = "http://127.0.0.1:8766/?case_id=iraq-2026-nisar-gcov-diagnostic"
CASE_ID = "iraq-2026-nisar-gcov-diagnostic"
EXPECTED_TEXT = (
    "No change finding exists to challenge",
    "PAIR QA GATE",
    "FAIL",
    "No temporal change was computed",
    "One QA-held diagnostic NISAR observation",
)


def require_loopback_url(url: str, parser: argparse.ArgumentParser) -> None:
    target = urllib.parse.urlsplit(url)
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
        parser.error(f"--url must be a loopback HTTP URL selecting case_id={CASE_ID}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="local interactive ECHO Iraq case URL")
    parser.add_argument("--geckodriver", help="geckodriver executable path")
    args = parser.parse_args()
    require_loopback_url(args.url, parser)

    port = get_free_port()
    driver_path = find_geckodriver(args.geckodriver)
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
            '&& document.querySelector("#caseSelector")?.value === '
            f'"{CASE_ID}" && document.querySelector("#challengeCaseObservation")?.hidden === false '
            '&& document.querySelector("#footprintMap").innerHTML.length > 500',
            timeout_seconds=30,
        )
        browser.execute(
            session_id,
            'window.__echoApiCalls=[]; window.__echoPageErrors=[]; '
            'window.addEventListener("error", event => window.__echoPageErrors.push(event.message)); '
            'const originalFetch=window.fetch.bind(window); '
            'window.fetch=(input, init={}) => { '
            'if (String(input).includes("/api/")) window.__echoApiCalls.push({'
            'url:String(input),method:(init.method||"GET").toUpperCase()}); '
            'return originalFetch(input,init); }; return true',
        )
        browser.click(session_id, "#challengeCaseObservation")
        browser.wait_for(
            session_id,
            'return document.querySelector("#adversarialChallengeDialog").open '
            '&& document.querySelector("#adversarialChallengeContent").innerText '
            '.includes("No change finding exists to challenge")',
            timeout_seconds=20,
        )
        result: dict[str, Any] = browser.execute(
            session_id,
            'return {text:document.querySelector("#adversarialChallengeContent").innerText,'
            'api_calls:window.__echoApiCalls,page_errors:window.__echoPageErrors}',
        )
        missing = [phrase for phrase in EXPECTED_TEXT if phrase not in result["text"]]
        if missing:
            raise AssertionError(f"challenge panel omitted required QA boundary text: {missing}")
        if any(call["method"] != "GET" for call in result["api_calls"]):
            raise AssertionError(f"challenge interaction submitted a write: {result['api_calls']}")
        if len(result["api_calls"]) != 1 or "adversarial-challenge" not in result["api_calls"][0]["url"]:
            raise AssertionError(f"unexpected local API traffic during challenge: {result['api_calls']}")
        if result["page_errors"]:
            raise AssertionError(f"browser reported JavaScript errors: {result['page_errors']}")

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "case_id": CASE_ID,
                    "required_scientific_boundary_text": list(EXPECTED_TEXT),
                    "api_calls": result["api_calls"],
                    "page_errors": result["page_errors"],
                    "interpretation_limit": "QA-held single-scene preview; no temporal result",
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
