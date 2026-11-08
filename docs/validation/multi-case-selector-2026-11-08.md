# Local multi-case selector validation

**Date:** 2026-11-08  
**Result:** Software and HTTP integration checks passed; browser interaction not verified

## Scope

The local interface discovers reviewed cases under `data/cases`, publishes their case IDs and review labels through `/api/cases`, and resolves each case-dependent request against the registered catalog. The interface preserves an explicitly selected case in the URL and applies its ID to data requests.

The HTTP integration check exercised automatic discovery from the repository, confirmed that both T024 and T163 expose their linked assessments, selected the T024 assessment through `case_id`, and confirmed that an unregistered ID returns HTTP 404. The test also checks the default case ID. It does not claim that the browser selector was clicked or visually inspected.

The case header now includes an `OPEN CASE INVESTIGATION` action only for registry entries with a linked assessment. It uses the same checksum-aware assessment loader as the contextual optical inspector, while cases without an assessment omit the action. The HTTP/UI-source test checks that the control is served; its browser click behavior was not exercised in this run.

## Verification

- `PYTHONPATH=. .venv/bin/pytest -q`: **298 passed**.
- `python3 -m compileall -q echo`: passed.
- `git diff --check`: passed.

## Limits

The selector changes which retained case record the existing application loads. It does not generalize the underlying product-specific measurement pipeline, validate any scientific conclusion, or change QA dispositions. Browser interaction and layout remain unverified because a fresh browser session was unavailable in this environment.
