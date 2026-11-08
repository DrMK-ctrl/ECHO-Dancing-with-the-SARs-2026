# Show evidence role and recorded status with hypothesis links

**Date:** 2026-11-08
**Status:** Implemented in the product-independent reasoning view

## Decision

For each evidence relationship shown under a hypothesis, display the linked artifact's declared role and record status beside the analyst-assigned relationship and rationale. Also show record status in the evidence-dependency list. Label it explicitly as an evidence-record status; do not reinterpret it as provider QA, scientific validity, independence, confidence, or proof.

## Rationale

Readers previously had to open each source record to learn whether it was diagnostic, quality-limited, contextual, or a derived analysis. Placing the role and recorded status beside `SUPPORTS`, `CONTRADICTS`, and other relationship labels makes the source scope visible where the interpretation is read, while retaining the source-inspection link.

## Verification and limits

- Headless Firefox executed the actual reasoning renderer with a controlled QA-held diagnostic SAR record and confirmed that role, record status, and relationship appear together.
- The full Python suite passed: **301 tests**.
- This is a presentation change. It does not assess the validity of the analyst-authored relationship or infer product QA from the generic artifact status.
