# Decision 0109: Align the browser directional-evidence guard

**Date:** 2026-11-09  
**Status:** Implemented and locally validated

## Context

The server's shared investigation contract blocks directional support or contradiction for a defined set of held, diagnostic, catalog-only, and synthetic evidence roles and statuses. The browser assessment form had a shorter role-only list. It could therefore offer a directional choice that the server would reject after submission.

## Decision

Keep the browser guard aligned with the authoritative role and status sets in `echo.investigation`. Disable `SUPPORTS` and `CONTRADICTS` when either set applies, show the user why the source is non-directional, and retain the server-side validation as the final gate. Add a regression test that compares both browser sets with the backend constants.

This is a user-workflow consistency fix. It does not determine whether other evidence is suitable, independently validate analyst-entered relationships, or alter any existing assessment disposition.

## Validation

The focused investigation, draft, and web API suites passed (135 tests). The full suite passed with `.venv/bin/python -m pytest -q` (441 tests). The direct `.venv/bin/pytest` entrypoint did not add the repository root to Python's import path in this environment and failed collection for research-tool imports; invoking pytest as a module resolved that environment-specific issue. `git diff --check` passed. No browser end-to-end run was performed.
