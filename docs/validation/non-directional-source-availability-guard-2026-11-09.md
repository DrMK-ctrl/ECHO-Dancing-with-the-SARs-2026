# Non-directional source-availability guard

Date: 2026-11-09

## Finding

The active T024 investigation contains ECOSTRESS catalog status `NO_GRANULES_IN_TARGET_INTERVAL` and ISMN inventory status `NO_SPATIOTEMPORALLY_SUITABLE_STATION`. Both are availability evidence, not physical measurements. They are currently unlinked from hypothesis relationships, so the audit found no existing directional claim to correct. Before this change, however, the shared contract would accept a later `SUPPORTS` or `CONTRADICTS` assignment to either record if the analyst set a matching disposition.

## Change

The shared contract now treats those exact statuses as non-directional evidence. Directional relationships are rejected; `DOES_NOT_DISTINGUISH` and `LIMITS_INTERPRETATION` remain available. The rule applies both when validating retained assessments and when assessing investigation drafts through the shared contract.

## Verification

- Added contract cases that attempt both a supportive ECOSTRESS availability claim and a contradictory station-coverage claim; both are rejected. Separate cases confirm that `DOES_NOT_DISTINGUISH` and `LIMITS_INTERPRETATION` remain valid for both availability states.
- `PYTHONPATH=. .venv/bin/pytest -q tests/test_investigation.py tests/test_investigation_scenarios.py tests/test_investigation_draft.py tests/test_web.py::test_all_active_case_assessments_validate_open_follow_up_designs --tb=short` — **90 passed**.
- The active T024 and T163 assessments still pass source-linked validation and their open follow-up test-design checks.
- Full software suite: `PYTHONPATH=. .venv/bin/python -m pytest -q --tb=short` — **412 passed**.
- `git diff --check` passed.

This guard controls how availability records can enter a hypothesis disposition. It does not establish whether either screened route was comprehensive or whether the underlying physical hypothesis is supported.
