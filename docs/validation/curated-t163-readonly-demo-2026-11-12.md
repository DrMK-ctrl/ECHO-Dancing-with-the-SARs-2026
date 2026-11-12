# T163 curated read-only investigation walkthrough — 2026-11-12

## Result

The T163 Rio Grande do Sul case opens in the single-case read-only mode using a separate, minimal evidence root. The browser connects the retained diagnostic Sentinel-1-derived OPERA RTC-S1 pair, NASA DSWx-HLS context, acquisition chronology, six recorded explanations, evidence relationships, sensitivity checks, and the **Challenge This Finding** review. The water-change explanation remains unresolved and not testable with the retained evidence; the UI states that OPERA has no consolidated provider QA disposition and is not NISAR.

This demonstrates an integrated diagnostic investigation workflow. It does not establish a validated flood extent, physical cause, provider QA pass, or NISAR temporal result.

## Curated evidence root

A temporary bundle was assembled from the case's `investigation.json`, its ten direct evidence records, all 25 source records linked by the cross-sensor assessment, and recursively referenced local source artifacts. The closure contained 65 files and 5,312,290 bytes. Missing references were treated as an error during assembly.

- Case: `rio-grande-do-sul-t163-349925-diagnostic-2024`
- Case manifest SHA-256: `b746a4c9f1e5d10121641f152111e651629dce042bc64220b333d1c82e4805ca`
- Cross-sensor assessment SHA-256: `d54aefa9979a976b2feb78841647fb9700c2fb2fce892e0036b1b7e979b009a9`
- Temporary evidence root used for this check: `/tmp/echo-t163-curated-check-20261112`

The temporary bundle was not copied into the repository or distributed. It contains no Earthdata credentials. Redistribution rights for every source and a clean-account distribution build remain unreviewed.

## Runtime and browser checks

The source-tree CLI was bound to `127.0.0.1:8768` with `--read-only-demo`, `--data-root`, and the T163 case catalog. HTTP checks returned 200 for `/`, `/api/cases`, `/api/case`, `/api/review`, `/api/cross-sensor-assessment`, `/api/adversarial-challenge?hypothesis_id=H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE`, and `/api/dswx-context`.

Firefox headless opened the assessment and challenged the retained H2 water explanation. It displayed:

- 1,199 / 1,199 common-clear cells and a recomputed median of −1.657 dB from the linked pair record;
- WTR / WTR-2 optical class counts and the different-grid, non-ground-truth limitations;
- `NOT TESTABLE WITH RETAINED EVIDENCE` and the absent consolidated OPERA QA disposition;
- a source-linked assessment checksum and explicit statement that diagnostic or unresolved QA cannot support a validated change claim.

The `/api/catalog` and `/api/opera-pair-analysis` POST routes and `/api/investigation-drafts` GET route each returned HTTP 403 `READ_ONLY_DEMO`. No provider search or data retrieval was performed in this mode. The browser screenshot is [`curated-t163-readonly-challenge-2026-11-12.png`](assets/curated-t163-readonly-challenge-2026-11-12.png).

## Reproduction command

From the ECHO repository root with the project environment installed:

```bash
.venv/bin/echo serve --read-only-demo \
  --case-file data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json
```

Open `http://127.0.0.1:8765/`. Stop with Ctrl+C. This uses the repository's complete local evidence root; it does not need the temporary bundle created for the isolation check. The application can still request optional NASA GIBS map context when network access is available.

## Limits

- Same development host and source checkout; not a wheel-installed T163 demo, separate Ubuntu account, or external judge deployment.
- OPERA RTC-S1 remains Sentinel-1-derived diagnostic evidence with no consolidated provider QA pass/fail disposition.
- The sensitivity checks are descriptive and do not establish a cause or independent validation.
- Bundle redistribution rights, clean OS-account acceptance, offline operation, and remote authentication remain unverified.
