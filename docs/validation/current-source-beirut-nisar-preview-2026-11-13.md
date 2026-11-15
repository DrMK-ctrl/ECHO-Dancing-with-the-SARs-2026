# Current-source Beirut NISAR measurement preview

**Acquisition:** 2026-10-10 16:24:36–16:25:11 UTC
**Observation:** `NISAR_L2_PR_GCOV_032_151_D_071_2005_DHDH_A_20261010T162436_20261010T162511_P05023_N_F_J_001`
**Checkout HEAD:** `2a13d8860309b4ad074ba69a7eaa9851a098cc63` (local worktree contained additional uncommitted changes)
**Status:** `QA_HELD_DIAGNOSTIC_PREVIEW`

## Source and selection

The saved ASF catalog search at
[`beirut-nisar-gcov-catalog-search-2026-11-13.json`](../../data/research/beirut-nisar-gcov-catalog-search-2026-11-13.json)
was retrieved at `2026-11-13T17:01:45.356746Z` for provisional GCOV over
`[35.53, 33.85, 35.55, 33.87]` WGS84 on 2026-10-10. It returned two metadata
features, including this scene, and no metadata-compatible temporal pair. The
catalog record SHA-256 is
`02810af091a20b7d2b0f09d9a41ef0b8fc21e5b7c9f9e7546f072e43909e99ef`.

The current-source bounded read is retained in
[`beirut-nisar-gcov-diagnostic-preview-current-source-2026-11-13.json`](../../data/research/beirut-nisar-gcov-diagnostic-preview-current-source-2026-11-13.json),
SHA-256 `68ece154cec98ce4bc1173f2ba719df4edefa984cc745631d203837439f3aace`.
It reads frequency A / HHHH, whose stored samples are linear gamma-zero power;
ECHO records that it applied no scale or offset. The 113 × 95 enclosing window
is EPSG:32636 and contains 10,266 selected AOI pixel centers. All 10,266 pass
the preview's display screen. This is one observation, not a change result.

The current product-layer attributes are retained and hashed. HHHH attributes
include `_FillValue=NaN`, the covariance-term description and long name,
`units=1`, and `valid_min=0.0`; their canonical JSON SHA-256 is
`f2d12bb7a3dd77990a252216ed870a8c7b27274e5d183aae6c8f78da876e3652`. The
source quality-layer attribute record SHA-256 is
`ddac8b5f317c81232913f0e71a2c28f8cad5fcef39b00c439dcc09cdbbb6f353`. The
seven array hashes are in the JSON record and were compared with the earlier
retained Beirut preview; all matched.

To repeat the provider-backed bounded read from the retained catalog result,
with the optional NISAR dependencies installed and Earthdata Login configured
locally in `~/.netrc`:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from echo.gcov_preview import build_gcov_preview

catalog = json.loads(Path(
    "data/research/beirut-nisar-gcov-catalog-search-2026-11-13.json"
).read_text())
scene_id = (
    "NISAR_L2_PR_GCOV_032_151_D_071_2005_DHDH_A_20261010T162436_"
    "20261010T162511_P05023_N_F_J_001"
)
feature = next(
    item for item in catalog["features"]
    if item["properties"].get("fileID") == scene_id
)
record = build_gcov_preview(
    feature,
    bounds_wgs84=(35.53, 33.85, 35.55, 33.87),
    frequency="A",
    layer="HHHH",
)
Path("/tmp/echo-beirut-gcov-preview.json").write_text(
    json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
)
print(record["scientific_disposition"], record["source"]["provider_qa_status"])
print(record["checksums"])
PY
```

The source read is live and took about 1–2 minutes in this run; provider QA is
fetched again. It requires neither a product-wide download nor credentials on
the command line.

## Provider QA and ECHO disposition

The newly retrieved ASF QA summary is `FAIL`, with the identification-group
check failed. Its artifact SHA-256 is
`8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`. ECHO
keeps the observation as a QA-held diagnostic preview. The valid display mask
does not override the provider's failure; no temporal measurement or event
interpretation was computed.

The bounded read completed at `2026-11-13T17:01:05.186318Z` using 43 HTTPS
range fetches, 7,370,179 requested bytes, and 108.181684 seconds cumulative
fetch time. No complete HDF5 object was downloaded. These timings describe
this retrieval, not a stable performance guarantee.

## Browser verification

The current Firefox replay used the retained catalog and measurement records
as local responses; it made no second provider request. The map rendered the
real HHHH samples in the user-selected WGS84 window, kept the `PROVIDER QA
FAIL · no change result` warning visible, and allowed pixel inspection. The
selected pixel readout was row 12971, column 5068, linear gamma-zero `30.9233`,
display `14.90 dB`, mask code 1, 5.190571 looks, exception code 0. This is a
pixel measurement/readout, not an event finding.

The Firefox replay passed all checks: raster and AOI bounds rendered, QA-held
disposition remained visible, a map pixel was inspectable, source-record
identity matched, both source-attribute hashes verified, sample-handling text
was visible, only the two local replay responses were used, and there were no
browser errors. Command:

```bash
.venv/bin/python tools/validation/check_gcov_preview_browser.py \
  --url 'http://127.0.0.1:8766/?case_id=iraq-2026-nisar-gcov-diagnostic' \
  --preview data/research/beirut-nisar-gcov-diagnostic-preview-current-source-2026-11-13.json \
  --catalog data/research/beirut-nisar-gcov-catalog-search-2026-11-13.json \
  --require-source-attributes \
  --screenshot /tmp/echo-beirut-current-source-preview.png
```

The unaltered browser screenshot is
[`beirut-nisar-current-source-preview-firefox-2026-11-13.png`](assets/beirut-nisar-current-source-preview-firefox-2026-11-13.png).

This verifies current-source data access, provenance recording, and local
map/pixel/source-inspector integration for this bounded AOI. It does not
validate provider QA, a temporal comparison, or a scientific interpretation.
