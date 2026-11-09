# Incremental global NISAR GCOV acquisition screen — 2026-11-09

## Result

ASF returned no global NISAR GCOV scenes for acquisition date 2026-11-09 in BETA, PROVISIONAL, or VALIDATED maturity. Each query covered the half-open UTC date interval `[2026-11-09, 2026-11-10)`, completed one catalog page, and reported complete coverage for that date window. The VALIDATED screen first ran at 01:16 UTC; it was rechecked at 12:04 UTC while checking the other maturities. No metadata temporal pair was available from these date-window results.

| Maturity | Scenes | Candidate pairs | Retrieval time (UTC) | Record SHA-256 |
|---|---:|---:|---|---|
| VALIDATED | 0 | 0 | 2026-11-09T01:16:56.892706+00:00 | `b922863e3babd50dd7368a49690bf3fd5b6694a449ec33484c2a08c7378708d2` |
| VALIDATED recheck | 0 | 0 | 2026-11-09T12:04:39.376362+00:00 | `fe4b52007ebdd978babc981fb147e6fc74859f98ecb69256f484f02fa58b71a5` |
| PROVISIONAL | 0 | 0 | 2026-11-09T12:04:56.914172+00:00 | `63ba53af47bc52c142255c8526368e24ed5383b71e93dca7b366a1f3e87e7a0f` |
| BETA | 0 | 0 | 2026-11-09T12:05:03.211484+00:00 | `f1dd4c0e611fda989e84c46da8a32b6f2d37b1b727a3e888464f08588560dd2b` |

The checksums cover the complete retained JSON records:

- [VALIDATED screen](../../data/research/validated-gcov-global-time-series-2026-11-09-2026-11-09.json)
- [VALIDATED recheck](../../data/research/validated-gcov-global-time-series-2026-11-09-recheck-1204Z.json)
- [PROVISIONAL screen](../../data/research/provisional-gcov-global-time-series-2026-11-09-2026-11-09.json)
- [BETA screen](../../data/research/beta-gcov-global-time-series-2026-11-09-2026-11-09.json)

## Interpretation boundary

This is a complete single-date catalog result, not evidence that the global NISAR archive lacks suitable observations on other dates, nor that future processing releases will not add this date. It is not a QA review or scientific suitability result. No products, measurement arrays, or raster windows were retrieved. Do not repeat the unchanged 2026-11-09 query; continue using the retained October–November catalog candidates and their documented QA status, or screen a later acquisition date when it becomes available.
