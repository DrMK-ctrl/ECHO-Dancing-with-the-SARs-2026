# T163 HLS coverage-cutoff sensitivity — 2026-11-09

The active T163 assessment now uses schema 3 and carries the source-linked sensitivity series for both NASA/USGS HLS sensors:

| Product | Minimum common clear-land optical area | SAR cells | Descriptive Pearson r (NDVI change vs. SAR log-ratio) |
|---|---:|---:|---:|
| L30 | 25% | 312 | −0.2130 |
| L30 | 50% | 265 | −0.2295 |
| L30 | 75% | 218 | −0.2905 |
| S30 | 25% | 39 | −0.1960 |
| S30 | 50% | 25 | −0.0489 |
| S30 | 75% | 11 | −0.4115 |

T163 has only 25 common clear-land S30 pixel centers (2.17% of its 1,152 AOI centers). The 75% cutoff leaves 11 SAR cells, so its descriptive correlation is especially sensitive to the selected support. These results do not provide inferential or causal evidence. The L30 and S30 products are separate optical streams, not independent confirmation; the Sentinel-1-derived RTC-S1 pair remains diagnostic without a consolidated QA disposition. H4 remains `UNRESOLVED` and `DOES_NOT_DISTINGUISH`.

The assessment builder recomputes both associations from the linked records and checksummed bounded subsets. The web validator checks that both cutoff series and each selected 75% summary match their corresponding association artifacts. Firefox rendered both T163 cards with their cutoff counts, correlations, and interpretation limits. The case manifest selects `data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-09-hls-cutoff-sensitivity.json`; the prior assessment remains retained.

The source-linked T163 assessment can be rebuilt using the retained-input command in [end-to-end workflow validation](end-to-end-investigation-workflow-2026-11-08.md), replacing its temporary output path with:

```text
data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-09-hls-cutoff-sensitivity.json
```

Verification:

- T163 and T024 builder tests passed with both HLS association variants.
- Active T163 web validation passed and rejects a modified S30 cutoff support count.
- Firefox rendered all six cutoff rows across the L30 and S30 cards.
- `.venv/bin/python -m pytest -q` — 388 passed.
- Python compilation and `git diff --check` passed.
