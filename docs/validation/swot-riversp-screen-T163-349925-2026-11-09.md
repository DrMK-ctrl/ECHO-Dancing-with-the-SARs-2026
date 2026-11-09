# SWOT RiverSP reach screen for the T163 case

Date: 2026-11-09
Case: `rio-grande-do-sul-t163-349925-diagnostic-2024`
Disposition: retrieved, quality-limited context; not used to validate the SAR measurement

## Question and method

Could NASA SWOT River Single-Pass reach observations near the two OPERA RTC-S1 acquisition dates provide independent hydrologic context for the roughly 1 km T163 analysis window?

The active OPERA pair dates are 2024-05-08 22:07 UTC and 2024-06-01 22:07 UTC. The reproducible screen queries each UTC day within six calendar days of either acquisition, then verifies complete CMR pagination and collection identity. The overlapping daily queries returned nine unique pass products after duplicate processing versions were resolved to the latest CMR `updated` value. The duplicate June 5 pass was resolved to `PGD0_02`. Nine protected Version D granules were downloaded using the local Earthdata configuration. Their CMR page response hashes, identities, retrieval URLs, byte counts, per-file SHA-256 checksums, acquisition times, retrieval timestamps, and extraction summaries are in the [structured record](../../data/research/swot-riversp-screen-T163-349925-2026-11-09.json).

For each granule, the reach shapefile was converted to GeoJSON with GDAL. Distances were calculated after transforming reach lines and the SAR analysis-window bounding rectangle from WGS84 to a local azimuthal-equidistant projection centered on the window. The summary covers reaches within 50 km of that window. The 50 km radius is a catalog-screening bound, not a claim that a reach at that distance represents local conditions.

## Result

No retained reach had NASA's `reach_q=0` (“good”) within 50 km in any of the nine retrieved granules. NASA's product documentation defines `reach_q=1` as suspect, `2` as degraded, and `3` as bad; suspect measurements may have large errors, degraded measurements very likely have large errors, and bad measurements may be nonsensical and should be ignored.

The nearest reaches in the May 6 and May 27 passes share reach IDs `64110700015` and `64120100055`, about 5.0 km and 8.0 km from the case-window bounds. Both dates mark these observations `reach_q=1`. The June 5 pass has no usable paired reach; its nearest suspect reach is 10.7 km away, while the nearest reach overall is marked bad and has no reported WSE. Other retrieved passes had no reach geometries within 50 km.

These data therefore do not pass a strict quality gate for corroboration, do not establish hydrologic connectivity to the case window, and do not validate a SAR-derived water boundary. No water-level difference or association with SAR measurements was computed. The screen is retained to prevent this specific route from being mistaken for accepted evidence or repeatedly searched without new grounds. The T163 assessment and its diagnostic SAR QA state are unchanged.

## Reproduction and references

Run from the repository root:

```bash
.venv/bin/python tools/research/screen_swot_riversp_reaches.py \
  --pair-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output data/research/swot-riversp-screen-T163-349925-2026-11-09.json \
  --window-days 6 \
  --radius-km 50
```

The command uses Earthdata Login from the local `.netrc`, CMR, GDAL `ogr2ogr`, `pyproj`, and Shapely. ZIP files are temporary; the output preserves source links and checksums so a rerun can verify that the retrieved objects are unchanged. It caps each granule at 100 MiB and the run at 500 MiB. A `reach_q=0` result is only a quality-screen candidate; spatial/hydrologic fit and an analyst-declared relationship remain separate decisions.

NASA product documentation: [SWOT L2 River Single-Pass Vector Reach Version D](https://podaac.jpl.nasa.gov/dataset/SWOT_L2_HR_RiverSP_reach_D), DOI `10.5067/SWOT-RIVERSP-D`; [Product Description Document](https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-docs/web-misc/swot_mission_docs/pdd/D-56413_SWOT_Product_Description_L2_HR_RiverSP_20250224a_RevC_clean_sig_final.pdf).
