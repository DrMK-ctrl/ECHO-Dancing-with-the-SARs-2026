# Investigation revision primary-source resolution

## Defect and correction

Starting a new assessment round selected the first artifact whose role was in the broad non-directional evidence set. That set includes metadata-only discovery records as well as SAR sources. A valid saved assessment with its catalog record before its SAR artifact could therefore try to rebuild the next round from catalog metadata.

Revision creation now uses the same unique primary-SAR-by-role resolver as draft validation and adversarial challenge assembly. It also preserves each staged catalog or provider-QA record's original follow-up ID, test design, and source checksum as inherited lineage. This lets the new round target another hypothesis without relabeling an earlier search as though it tested the new question. The active follow-up starts in `NOT_SEARCHED`, hypotheses reset for fresh assessment, and the primary source retains its QA status. Local snapshot storage verifies that the inherited lineage exactly matches the immutable parent.

## Verification

- The regression reproduced the failure with a valid assessed draft whose staged ASF catalog record preceded the primary SAR artifact.
- The first fix exposed a second continuity defect: changing the follow-up hypothesis left its prior catalog query incorrectly required to match the new test design.
- After the fix, the new round resolves the exact SAR evidence ID, carries the catalog record and its original test link forward, starts the new test as unsearched, resets all hypotheses to `NOT_EVALUATED`, and preserves `QA_HELD`.
- The local draft store saves and reloads the parent-linked revision; altered inherited test-design lineage is rejected.
- Full suite: **483 passed**. Python compilation and `git diff --check` passed.
- The existing regression for revising a reordered draft and targeting a different hypothesis also passes.

This changes source selection and draft continuity only. It does not alter measurements, validate provider QA, or add a scientific conclusion.
