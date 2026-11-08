# Follow-up catalog-window alignment — 2026-11-08

## Result

Newly attached ASF catalog records retain the interval registered in the follow-up test and the interval actually present in the catalog query. The validator recomputes the comparison and confirms that its planned interval matches the current test design. New records use schema version 2 and reject a missing or falsified comparison; legacy schema version 1 records remain supported. The investigation evidence view renders the state and both intervals with an explicit filter-only limitation.

## Verification

- Focused investigation-draft and web tests: **59 passed**.
- Focused cases cover an unplanned interval, a deviating query, tampered comparison state, and a removed comparison with refreshed evidence checksums. The full suite also passes against retained records and fixtures.
- Full test suite: `PYTHONPATH=. ./.venv/bin/pytest -q` — **360 passed**. The explicit `PYTHONPATH` is needed for this checkout's uninstalled `tools.research` namespace package.
- Firefox headless against the local ECHO server rendered a deviating catalog query and showed `DEVIATES FROM PLANNED WINDOW`, both planned and executed intervals, and `date-filter comparison only`.
- `./.venv/bin/python -m compileall -q echo` and `git diff --check` — passed.

## Limits

This detects date-filter drift between the plan and the submitted catalog query. It does not prove that a scene exists inside the interval, covers the AOI, is suitable for the test, or passes QA. Catalog results remain metadata-only.
