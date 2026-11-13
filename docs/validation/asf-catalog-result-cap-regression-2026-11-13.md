# ASF catalog result-cap regression check — 2026-11-13

## Purpose

The NISAR GCOV client previously passed the same `maxResults` value both in
`ASFSearchOptions` and as the `search_generator` keyword. The installed
`asf_search` client warned that the keyword replaced the option. ECHO now passes
the cap once, through `search_generator`, while retaining the same pagination
and local result-limit handling.

## Live bounded check

The current client ran this public metadata-only query against ASF CMR:

```bash
.venv/bin/echo catalog \
  --longitude 44.36 --latitude 33.31 \
  --start 2026-10-01 --end 2026-10-12 \
  --maturity PROVISIONAL --max-results 1000 \
  --output data/research/asf-catalog-result-cap-regression-2026-11-13.json
```

The query returned two catalog features in one page. No result-cap override
warning was emitted, the result set was below the 1,000-feature cap, and
`potentially_truncated` is false. The response record has SHA-256
`21b313f19c2c3a191babfebd42d7fbed5e1b39b0dcdec4462bb967122d915512` and records
the query timestamp, provider, result cap, and exact scene identifiers.

This is catalog and client-integration evidence only. It does not establish
pixel coverage, product QA, suitability for comparison, or any surface-change
measurement. No product or QA artifact was fetched.
