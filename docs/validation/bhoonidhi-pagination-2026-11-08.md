# Bhoonidhi bounded pagination validation

**Date:** 2026-11-08

## Scope

Verified ECHO's local Bhoonidhi S-SAR GCOV client against mocked STAC responses. The check covers continuation mechanics and token boundaries; it does not validate a live Bhoonidhi account, actual S-SAR catalog items, product availability, or product QA.

## Results

- `.venv/bin/python -m pytest tests/test_bhoonidhi.py -q --tb=short` — **13 passed**.
- `.venv/bin/python -m pytest -q --tb=short` — **349 passed**.
- `.venv/bin/python -m compileall -q echo tests` — passed.
- `git diff --check` — passed.

The focused cases verify sequential GET paging, POST paging with merged query body, continuation headers, per-page hashes and counts, combined feature count, hard page-cap status, and rejection of cross-origin or repeated continuation requests. Credentials and access tokens are not included in the returned record.

## Limits

No registered Bhoonidhi credentials were available, so these results do not prove the provider's live `next` links use the exercised combinations. ECHO keeps the result explicitly incomplete when its page cap is reached. The catalog client remains a CLI workflow and is not connected to the geographic map or product retrieval path.
