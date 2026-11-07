# Live paired GCOV API: provider QA hold

**Validated:** 2026-11-07  
**Scope:** Live HTTP path and provider-QA gate only; no raster processing

## Request and result

ECHO's local HTTP server received a real `POST /api/gcov-pair-analysis` request for the sole metadata-compatible pair in the retained global VALIDATED GCOV scan. The products share collection `NISAR_L2_GCOV_V1`, CRID `P05036`, ascending path 11, and frame 17; their acquisition starts are 12 days apart.

| Role | Acquisition start (UTC) | Orbit | Provider QA | QA artifact SHA-256 |
|---|---|---:|---|---|
| Before | 2026-10-24 22:49:55 | 6511 | **FAIL** | `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688` |
| After | 2026-11-05 22:49:56 | 6684 | **FAIL** | `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688` |

The endpoint returned HTTP 200 with `status=QA_HELD` and both roles listed as held. It reported `product_identification=NOT_EVALUATED`, `measurement_arrays=NOT_READ`, `grid_alignment=NOT_EVALUATED`, and `change_calculation=NOT_PERFORMED`. Both `measurement` and `manifest` were null. The provider statuses were preserved as returned; ECHO made no reinterpretation.

The machine-readable request and full response, including retrieval times, source URLs, QA check rows, and catalog-snapshot checksum, are preserved in [`nisar-live-pair-api-qa-hold-2026-11-07.json`](../../data/research/nisar-live-pair-api-qa-hold-2026-11-07.json). Its SHA-256 is `a0331b37decbec429bac057c7662af32c87ce8e58c9bc4e1f6e0a6206730901f`.

## Interpretation boundary

This live request verifies that the paired API retrieves both canonical provider QA records and stops before product identification and raster reads when either role is non-PASS. It is stronger than the unit-level early-return test, but it does not establish product compatibility at pixel level, a measured temporal change, or an event interpretation. A QA-cleared real pair is still required for those claims.
