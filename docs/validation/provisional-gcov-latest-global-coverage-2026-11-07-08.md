# Latest global NISAR PROVISIONAL GCOV coverage — 2026-11-07 to 2026-11-08

## Result

An incremental global ASF catalog screen of the two acquisition dates not covered by the previous PROVISIONAL screen found no NISAR GCOV scenes and therefore no new temporal pair. This is a date-window coverage result only; it says nothing about acquisitions on other dates or future catalog updates.

## Query evidence

The previous retained global PROVISIONAL search ended on 2026-11-06. ECHO queried 2026-11-07 and 2026-11-08 separately using `asf_search`, dataset NISAR, processing level GCOV, and one daily half-open time window per date.

- The first request for 2026-11-07 timed out at the 30-second CMR limit. The original incomplete response is retained in [`provisional-gcov-global-time-series-2026-11-07-08.json`](../../data/research/provisional-gcov-global-time-series-2026-11-07-08.json), SHA-256 `3af17af5c885051bcbc6aedde5d6407fdfe0c9002574fecad513764055d03b5e`.
- A single retry of 2026-11-07 with a 90-second CMR timeout completed: one page, zero features, no result cap. Its record is [`provisional-gcov-global-time-series-2026-11-07-retry-2026-11-08.json`](../../data/research/provisional-gcov-global-time-series-2026-11-07-retry-2026-11-08.json), SHA-256 `dda4411fe27dd99c8b1b2fa45b0e5371c87d5ddf846bf288908d1062af82ce75`.
- The 2026-11-08 request completed at the standard 30-second timeout: one page, zero features, no result cap. The same first record retains this response.

Both date windows are now complete for this screen. The available records establish **zero returned scenes and zero metadata pairs** for these two dates in the PROVISIONAL GCOV catalog at the retrieval times. Since no product was returned, there was nothing to QA-screen. This does not establish a global absence beyond these dates or this catalog maturity.

## Consequence

This incremental screen does not change the status of older QA-held scenes or produce a temporal measurement. The current NISAR validation route remains dependent on a new suitable, QA-accepted pair; further work should target a distinct acquisition window or a scientifically appropriate complementary dataset rather than retrying these completed dates.
