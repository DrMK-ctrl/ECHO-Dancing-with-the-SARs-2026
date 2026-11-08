# Inline evidence status in hypothesis review

## Check

Headless Firefox loaded the local ECHO interface and executed the product-independent investigation renderer with one controlled hypothesis referencing a QA-held diagnostic SAR record.

## Result

- The relation card displayed `LIMITS INTERPRETATION`, the evidence role `DIAGNOSTIC SAR MEASUREMENT`, and `EVIDENCE RECORD STATUS: QA HELD` together.
- The existing source identifier remains a clickable evidence-inspection control.
- `.venv/bin/python -m pytest -q` — **301 passed**.

## Limits

The renderer input was a controlled record fixture, not an evaluation of the scientific correctness of the relationship or a new SAR result. The displayed record status is source metadata and is not itself a QA or validation verdict.
