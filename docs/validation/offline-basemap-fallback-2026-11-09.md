# Offline basemap fallback — 2026-11-09

## Result

The map workspace remains usable when NASA GIBS imagery cannot load. A failed request now leaves the coordinate grid and catalog footprints in place, reports the basemap as offline, and avoids retrying it on every map redraw. The user can hide the unavailable context layer and turn it back on to retry.

## Runtime check

Opened the local ECHO application in headless Firefox with a retained Istanbul case containing six dated catalog footprints. Firefox used a local, unreachable HTTP/HTTPS proxy for external requests while the loopback ECHO server remained reachable. The NASA GIBS image request failed as intended.

- After failure, the map contained ten coordinate-grid lines and all six catalog footprints; the GIBS image element was removed.
- The control showed `GIBS OFFLINE`, had `aria-pressed=false`, and its title explained how to hide the layer or retry it.
- Zooming redrew the map without issuing another GIBS request and kept the offline status visible.
- Turning the context layer off preserved the grid and footprints. Turning it back on made exactly one new GIBS request; with the external proxy still unavailable, the fallback state returned.

This verifies client-side degradation and retry behavior, not actual GIBS availability, offline access to remote catalogs, or offline operation of the entire application backend.

## Reproduction

From the repository root:

1. Start the local server with the repository's default case registry.
2. Start Firefox headless with external HTTP and HTTPS directed to an unreachable local proxy, while allowing `localhost` and `127.0.0.1` directly.
3. Open `/?case_id=istanbul-2026-flood`, wait for the GIBS image error, inspect `#footprintMap` and `#toggleBasemap`, then zoom and toggle the basemap off and on.

The 2026-11-09 run also checked the modified JavaScript in the live Firefox runtime, ran `git diff --check`, and passed the full repository suite with `PYTHONPATH=. .venv/bin/pytest -q` (424 passed).
