# T163 native-grid spatial support validation

**Result:** A reproducible descriptive cross-sensor overlay is linked to the case assessment; the water explanation remains unresolved.

## Method and result

The evaluation transforms each retained NASA OPERA DSWx-HLS WTR cell polygon into the RTC-S1 projected CRS, intersects it with the retained SAR pixel polygon, and weights valid before/after water classes by exact overlap area. Neither product is resampled. Only WTR cells with valid codes at both dates contribute. RTC-S1 common-clear and finite-value masks are required.

The T163-349925-IW2 pair spans about 24 days. The optical products are NASA OPERA DSWx-HLS classifications derived from HLS observations; their acquisitions are near the corresponding SAR times. The RTC-S1 pair remains diagnostic because its product QA metadata have no consolidated provider PASS/FAIL disposition.

The retained AOI record has 1,254 SAR window cells, 1,199 valid SAR measurements, 1,199 serialized optical cells, and 837 WTR cells valid at both optical dates. At a 0.75 minimum common-valid optical area fraction, 738 SAR cells remain. Of these, 710 have at most 0.05 water-fraction change; 14 increase and 14 decrease by more than 0.05. Median water-fraction change is 0. The descriptive Pearson correlation with the signed SAR log-ratio is −0.108. Sensitivity summaries at 0.50, 0.75, 0.90, and 0.95 coverage are stored in the record.

This result does not distinguish the water explanation. The small number of changing cells and weak linear association do not establish that no water change occurred. No inferential statistic is reported because neighboring cells are spatially dependent and no suitable spatial evaluation design was specified. DSWx-HLS remains optical algorithm context, not field truth or SAR validation. No causal conclusion or flood boundary is made.

## Integration and verification

- `tools/research/evaluate_rtc_dswx_spatial_support.py` creates the checksum-linked per-SAR-cell record and checks expected product types, statuses, WTR classes, CRS metadata, AOI bounds, shapes, and masks.
- `tools/research/build_cross_sensor_investigation.py --spatial-support-record ...` verifies the exact input-record hashes and links the overlay to the water hypothesis as `DOES_NOT_DISTINGUISH`. The hypothesis remains `UNRESOLVED` and `NOT_TESTABLE_WITH_RETAINED_EVIDENCE` because QA and scientific sufficiency gates remain unmet.
- The interface shows the coverage summary and a cell-level evidence inspector. The local API resolves evidence IDs only through the case-linked assessment and verifies artifact checksum, identity, and source-record checksums before serving the record.
- Synthetic geometry tests verify fractional area aggregation, invalid-class exclusion, QA refusal, grid mismatch refusal, and mask immutability. They are software fixtures, not satellite evidence.
- Firefox headless opened the retained case, loaded optical context, opened the linked assessment, displayed the spatial-support card, and retrieved all 1,254 cell records through the evidence inspector. The assessment remained `CAUSAL_INTERPRETATION_UNRESOLVED`. See the [captured evidence card](opera-t163-spatial-support-card-2026-11-08.png).
- Full repository suite: `239 passed`. The focused overlay and assessment contracts are in `tests/test_rtc_dswx_spatial_support.py`, `tests/test_cross_sensor_investigation.py`, and `tests/test_web.py`.

## Artifact checksums

- Spatial overlay record: SHA-256 `ce836d57757cf7208ee9b88b17a9e503443e1a391aec0d00c4b68c0812c7bcfe`.
- Updated T163 assessment: SHA-256 `0a4887c79e4bf96fab2f76541fa71d2dff448b2433d6c9c059d9b94854eea89c`.
- Browser evidence card: SHA-256 `497adaf859e99be73adc2c4dc5bcb38908a40a6e74b2f9bd6232f8adbc4d553d`.
- Overlay script: SHA-256 `1fd82acd6ab50ba057c2ead1da452740c2f6c21f5d9f0fb334f8c87a1a4cbf13`.
- Assessment builder: SHA-256 `7de6ec79e9143aef60f159912cb59bd0fd40d5f9fa6785353ded816549921ad5`.

Reproduce the analysis and assessment from the repository root:

```bash
.venv/bin/python tools/research/evaluate_rtc_dswx_spatial_support.py
.venv/bin/python tools/research/build_cross_sensor_investigation.py \
  --sar-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical-record data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --catalog-screen-record data/research/dswx-hls-screen-T163-349925-2026-11-07.json \
  --spatial-support-record data/research/opera-rtc-dswx-spatial-support-T163-349925-2026-11-08.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-07.json
```

NASA source documentation: [PO.DAAC OPERA DSWx-HLS Version 1 dataset](https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-HLS_V1), DOI `10.5067/OPDSW-PL3V1`. The product documentation notes that WTR inherits HLS cloud, cloud-shadow, and snow/ice labels and that WTR-2 has different masking behavior; those product limits are why the overlay remains contextual and diagnostic.
