# Single-hypothesis test-target validation

Date: 2026-11-08

## Scope

Verified that open discriminating test designs cannot target multiple hypotheses while declaring only one hypothesis under test. Shared quality-gate follow-ups without a discriminating test design retain their existing ability to address multiple hypotheses.

## Evidence

- A synthetic contract fixture with two follow-up targets and one declared hypothesis is rejected with `test design must target exactly its one hypothesis under test`.
- Existing generated open test designs in both retained Rio Grande do Sul assessments target exactly one hypothesis.
- `echo.web._validate_assessment_record` accepted the T024 record (4 evidence artifacts, 3 single-hypothesis designs) and T163 record (18 evidence artifacts, 3 single-hypothesis designs).
- Full automated suite: `.venv/bin/python -m pytest -q` — 279 passed. Python compilation and `git diff --check` passed.
- This validates test-scope consistency only. It does not establish that a hypothesis, prediction, or evidence relationship is scientifically correct.
