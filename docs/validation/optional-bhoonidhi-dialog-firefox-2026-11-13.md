# Optional Bhoonidhi authentication dialog — Firefox check

**Date:** 2026-11-13
**Application:** local interactive workbench at `127.0.0.1:8766`
**Result:** PASS; no credentials entered and no Bhoonidhi request submitted.

## Browser flow

Headless Firefox opened the local ECHO workbench, opened **NISAR S-SAR**, and confirmed the dialog explains that the catalog search is optional, requires a registered Bhoonidhi account, and returns metadata only. Both credential fields were empty. Closing the dialog returned to a rendered case workspace with its case selector available. The browser-side request counter recorded zero Bhoonidhi requests.

The same run retained the map interaction checks: pinch-style wheel events zoomed around the gesture point; ordinary wheel scrolling was not intercepted; AOI drawing remained active during the gesture; and no catalog request was sent. These are browser-simulated gestures, not a physical laptop touchpad test.

Reproduce with the local interactive workbench already running:

```bash
.venv/bin/python tools/validation/check_map_area_browser.py \
  --url http://127.0.0.1:8766
```

This verifies the local guest path and dialog behavior only. It does not verify Bhoonidhi authentication, live S-SAR catalog availability, product retrieval, or S-band measurements.
