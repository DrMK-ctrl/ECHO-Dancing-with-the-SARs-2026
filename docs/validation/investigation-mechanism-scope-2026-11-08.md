# Investigation mechanism-scope validation

Date: 2026-11-08

## Scope

Validated the assessment-builder refactor that separates soil moisture, vegetation, acquisition conditions, and SAR product quality into distinct hypotheses and follow-up tracks. Both retained Rio Grande do Sul assessments were regenerated from their existing source records. No satellite data were newly retrieved or reprocessed in this change.

## Checks

- T163 H3 contains GPM/SMAP evidence only; H4 contains the L30/S30 vegetation associations only; H5 remains not evaluated without evidence; H6 retains the product-quality limitation.
- T024 and T163 records pass the web assessment-record validator.
- Focused automated tests: `.venv/bin/python -m pytest -q tests/test_cross_sensor_investigation.py tests/test_case_records.py` — 22 passed.
- Full automated suite: `.venv/bin/python -m pytest -q` — 278 passed.
- Headless Firefox opened the T163 assessment in the local application and rendered all six hypothesis statements, including the new soil-moisture, vegetation-state, acquisition-condition, and product-quality branches.

## Result and limits

The structure now keeps each evidence search tied to one declared mechanism, and identifies alternatives outside that test's scope. Existing causal dispositions remain unresolved or not evaluated. This verifies record consistency and software behavior; it does not validate the diagnostic OPERA RTC-S1 measurements, establish any mechanism, or constitute scientific confirmation.
