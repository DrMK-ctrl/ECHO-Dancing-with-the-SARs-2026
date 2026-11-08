# Investigation evidence integrity impact check

## Scope

Exercised the rejected-assessment path after a manifest-linked source changes. The test fixture is synthetic and is used only to verify checksum and dependency behavior.

## Results

- The assessment endpoint returns HTTP 409 with `REASSESSMENT_REQUIRED` and does not return the stale assessment.
- The impact report retains the assessment SHA-256 and reports the source's expected and observed hashes.
- A derived artifact is marked affected through its declared lineage; the linked hypothesis and follow-up are identified.
- Headless Firefox exercised the assessment-opening error branch with a controlled HTTP 409 response. The dialog rendered the affected finding and follow-up; a script-like hypothesis string appeared as text and created no executable element.
- `.venv/bin/python -m pytest tests/test_web.py -q` — **28 passed**.

## Limits

This verifies software integrity handling using a synthetic fixture. It does not determine whether changed content is scientifically reliable, restore prior source bytes, rebuild an assessment, or validate nested file assets referenced inside source records.
