# Investigation evidence integrity impact check

## Scope

Exercised the rejected-assessment path after a manifest-linked source changes. The test fixture is synthetic and is used only to verify checksum and dependency behavior.

## Results

- The assessment endpoint returns HTTP 409 with `REASSESSMENT_REQUIRED` and does not return the stale assessment.
- The impact report retains the assessment SHA-256 and reports the source's expected and observed hashes.
- A derived artifact is marked affected through its declared lineage; the linked hypothesis and follow-up are identified.
- A separate GPM-like fixture keeps its manifest-linked JSON unchanged while altering a nested, checksummed daily asset; the endpoint identifies the parent evidence record and nested file path.
- Headless Firefox exercised the assessment-opening error branch with a controlled HTTP 409 response. The dialog rendered the affected finding and follow-up; a script-like hypothesis string appeared as text and created no executable element.
- `.venv/bin/python -m pytest tests/test_web.py -q` — **29 passed**.
- Full suite: `.venv/bin/python -m pytest -q` — **301 passed**.
- A second Firefox check verified that the current dialog renders the nested asset path, affected hypothesis and follow-up, and creates no script node from supplied text.
- The live local assessment endpoint still returned both retained T024 and T163 records with HTTP 200 (`CAUSAL_INTERPRETATION_UNRESOLVED`; 5 and 20 evidence artifacts), confirming that their declared nested assets currently pass integrity checks.

## Limits

This verifies software integrity handling using synthetic fixtures. It does not determine whether changed content is scientifically reliable, restore prior source bytes, or rebuild an assessment. Nested references are reported only when the source record itself passes its recorded hash and identity checks and the nested path has a local SHA-256 reference.
