# Import and revalidation of investigation review notes

**Date:** 2026-11-08
**Disposition:** Same-assessment review import verified; scientific case data remain unchanged

## Procedure

In Firefox, the T163 assessment was opened and a reviewer created a hypothesis-specific challenge with a counterfactual source reclassification. The review notes were exported, the page reloaded, and the JSON export imported into the same case assessment. ECHO rendered the note and its counterfactual after recomputing the relationship change through the hash-bound preview API. The export retained the active assessment checksum and cited source checksum.

A second copy of that export was edited so its `counterfactual_disposition` disagreed with the deterministic result. After another reload, the modified file was rejected with “Counterfactual no longer reproduces against the current assessment.” No challenge note appeared in the assessment view.

## Limits

The importer verifies case identity, assessment and evidence hashes, hypothesis linkage, and counterfactual reproducibility. It cannot authenticate the human author or validate challenge prose. Imported notes stay `UNASSESSED_HUMAN_INPUT`, are held in browser memory, and do not alter provider QA, scientific evidence, or the retained assessment. Files are capped at 1 MiB and 100 notes.
