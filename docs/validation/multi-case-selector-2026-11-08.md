# Local multi-case selector validation

**Date:** 2026-11-08  
**Result:** Software, HTTP integration, and headless browser interaction checks passed; detailed visual review remains open

## Scope

The local interface discovers reviewed cases under `data/cases`, publishes their case IDs and review labels through `/api/cases`, and resolves each case-dependent request against the registered catalog. The interface preserves an explicitly selected case in the URL and applies its ID to data requests.

The HTTP integration check exercised automatic discovery from the repository, confirmed that both T024 and T163 expose their linked assessments, selected the T024 assessment through `case_id`, and confirmed that an unregistered ID returns HTTP 404. The test also checks the default case ID.

An isolated headless Firefox session exercised the actual UI: it opened the T163 assessment from the case header, changed the selector to T024 and opened that assessment, then changed to Nepal and confirmed the action is hidden because that case has no linked assessment. For both assessments the opened panel included the diagnostic SAR context. The action uses the same checksum-aware assessment loader as the optical inspector.

## Verification

- `PYTHONPATH=. .venv/bin/pytest -q`: **298 passed**.
- `python3 -m compileall -q echo`: passed.
- `git diff --check`: passed.

## Limits

The selector changes which retained case record the existing application loads. It does not generalize the underlying product-specific measurement pipeline, validate any scientific conclusion, or change QA dispositions. Detailed visual review remains open: the browser check covered desktop interaction at the driver's default headless viewport, but did not inspect screenshot styling or narrow-screen layout.
