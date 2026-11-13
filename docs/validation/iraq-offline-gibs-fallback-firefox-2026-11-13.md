# Iraq map fallback with external networking blocked

**Date:** 2026-11-13  
**Application:** interactive local workbench at `127.0.0.1:8766`  
**Browser:** Firefox headless, W3C WebDriver

Firefox opened the dated Iraq NISAR case while HTTP and HTTPS traffic outside
loopback was routed to an unreachable local proxy (`127.0.0.1:9`). The local
application remained reachable. The map's backdrop control was changed to the
NISAR GCOV browse mosaic, whose GIBS request failed under the blocked network.

The browser then showed `NASA GIBS UNAVAILABLE` and retained its local
Natural Earth coastline fallback. The map SVG remained 788 CSS pixels wide and
contained 134 coastline paths; the failed image element was removed. The
imagery selector remained set to NISAR, its title explained the failure and
retry action, and no visible alert or application error appeared.

The page had no selected-scene measurement loaded during this check. The
fallback is geographic context only; it says nothing about NISAR data
availability, measurement retrieval, provider QA, or scientific conclusions.
This verifies one browser fallback path with external networking unavailable,
not full application-wide offline operation.
