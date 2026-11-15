# Global exploration: live empty-catalog result — 2026-11-13

## Purpose

Verify that a real no-match catalog response in the current browser workflow is presented as a completed search with a clear next step, rather than as an application failure or an implied scientific finding.

## Run

- Checkout: `/home/mahdi-kheirddine/Projects/echo-dancing-with-the-sars-2026`
- Branch / HEAD: `main` / `2a13d8860309b4ad074ba69a7eaa9851a098cc63`; the worktree contained uncommitted changes.
- Local interface: loopback ECHO server at `http://127.0.0.1:8876/` and Firefox headless, 1440 × 1000 viewport.
- User flow: opened the default global exploration page; searched longitude `35.54`, latitude `33.86`, acquisition date `2026-11-12`, maturity `VALIDATED`.
- ECHO's browser-observed `POST /api/catalog` response was HTTP 200 with zero features. The response query echoed the exact point, date, and maturity. No browser errors were observed.

## What the user saw

The interface displayed **NO OBSERVATIONS**, explained that no NISAR GCOV observations matched the point and date, showed an empty acquisition timeline and observation record, and kept the analysis gates open. Its next-evidence panel directs the user to search an area/date interval and define independent reference evidence. It did not create a measurement, candidate pair, or finding.

The unaltered browser capture is [global-empty-catalog-result-live-2026-11-13.png](assets/global-empty-catalog-result-live-2026-11-13.png), SHA-256 `ff64219db71a10104e9c38329d693baa5f778f35643a661a9e2d1155a42c5d38`.

## Related retained catalog evidence

The same closed acquisition date was independently queried globally at all three GCOV maturities at approximately 17:34 UTC. Each complete one-day query returned zero scenes in one page with no errors or truncation. The exact responses and checksums are recorded in [the Nov 13 incremental screen](../research/2026-11-13-incremental-nisar-gcov-screen.md). The broader catalog record is not the exact point-query response; it supplies independent archive-wide date coverage context only.

The browser's point-query response body was inspected in memory during this run but was not saved as a separate JSON artifact. The screenshot and the retained global catalog records are therefore the durable evidence for this check; they do not establish that ASF's archive will remain unchanged.

## Map-focus correction and regression

The first capture exposed a map usability defect: after a successful point search from the global home, the evidence panel updated but the map stayed at the full-world extent. The search success handler now exits World View before drawing results. A Firefox rerun of the same live query showed a `0.1200000000°` longitude span centered at `35.54° E, 33.86° N`, while keeping `NO OBSERVATIONS` and the no-finding explanation intact. Clicking **World View** then restored the `360°` extent and the global-map caption. The no-match outcome did not change.

The post-fix browser capture is [global-empty-catalog-focused-live-2026-11-13.png](assets/global-empty-catalog-focused-live-2026-11-13.png), SHA-256 `89a6b02612d42a96a3e6d82dcca2f6176f1e6c7bf028401f47f47a88e9e02bbf`.

## Reproduce

Start the app with `.venv/bin/echo serve --host 127.0.0.1 --port 8876`, open its global page, choose **Find Observations**, and submit the point/date/maturity above. This sends a read-only catalog query to ASF. It does not retrieve product pixels or modify an investigation. Availability can change as the archive is updated.
