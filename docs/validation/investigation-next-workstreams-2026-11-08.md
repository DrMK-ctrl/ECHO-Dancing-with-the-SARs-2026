# Investigation next-workstream verification — 2026-11-08

## Implemented behavior

Follow-up records now receive a deterministic `action_track` from their declared purpose and availability. The T163 and T024 assessments were regenerated from their retained source records. In the T163 assessment, pending provider QA is labeled a quality prerequisite; the not-yet-searched surface-state observation is labeled a new evidence search; the nearer optical screen, spatial overlay, polarization check, and GPM context are labeled reviewed results.

The interface presents these as distinct workstreams and states that they are not a confidence or value ranking. It explicitly allows contextual research to proceed while provider QA is pending, while keeping acceptance of the diagnostic SAR measurement subject to the QA gate.

## Verification performed

- `PYTHONPATH=. .venv/bin/pytest -q` — **251 passed**.
- `git diff --check` and Python `compileall` — passed.
- Firefox headless against the local ECHO server — opened the T163 optical context and linked investigation assessment; confirmed the page displayed the separate quality-prerequisite and new-evidence-search tracks, plus reviewed-result entries.
- Both regenerated assessments retain `CAUSAL_INTERPRETATION_UNRESOLVED`. No QA disposition, hypothesis state, or measurement was promoted by workstream classification.

## Limits

The classification identifies action type and status; it does not estimate information gain, compare feasibility, automatically search a provider, or establish which scientific explanation is correct. Workstream labels are workflow guidance, not a ranking.
