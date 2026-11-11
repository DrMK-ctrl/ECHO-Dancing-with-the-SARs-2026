# Adversarial evidence challenge: scoped implementation

**State:** Implemented review workflow; not an autonomous causal evaluator.

## What the challenge does

`Challenge this finding` assembles a deterministic, read-only review from the active case assessment and its linked evidence. The API validates the assessment and its source records before returning the dossier. It keeps the observation, the selected hypothesis, analyst-recorded evidence relationships, competing explanations, linked sensitivity variants, unassessed evidence, and pre-recorded follow-up observations distinct. For T163, it also exposes the checksum-linked acquisition-condition review in a separate case-wide comparability lane when the selected hypothesis did not cite that review. The view labels that scope and does not convert it into directional evidence. Source-inspector links preserve access to the underlying records and checksums.

For a linked RTC-S1 pair, the challenge additionally verifies the pair-record checksum and identity, acquisition metadata and support counts. It recomputes the mean and median from the retained `values_db` array under the recorded valid and common-clear masks. It rejects a summary that does not reproduce. This checks arithmetic and record linkage; it does not establish product QA or validate an explanation.

## Existing-case behavior

- **T163 Rio Grande do Sul:** The selected water-change explanation remains `UNRESOLVED`; the RTC-S1 pair retains unresolved provider QA. The UI shows the actual acquisition interval and response summary, reports the reproduced measurement check, links the recorded OPERA polarization sensitivity source and other existing evidence, and exposes competing explanations and follow-up plans. Evidence relationships are labeled as analyst assessments. Existing sensitivity records are linked, but no aggregate stability verdict is calculated. This remains a diagnostic investigation, not a validated flood finding.
- **Acquisition comparability:** The challenge verifies the review record checksum and reproduces it against the linked pair metadata before returning it. The progressive UI groups this descriptive metadata comparison beside (but separately from) already linked sensitivity records. It shows missing incidence-angle and spatially matched RFI evidence, and explicitly states that matching metadata do not establish raster alignment or clear provider QA. When the review is not cited by the selected hypothesis, it is labeled case-wide and not linked to that hypothesis.
- **Iraq NISAR GCOV:** The case has one QA-held diagnostic preview and a candidate pair whose two products have provider QA `FAIL`. The challenge explicitly says there is no change finding to challenge, exposes the single-observation and QA records, and returns no change conclusion. It does not calculate temporal change or infer an event.

## What it does not claim or calculate

- It does not infer a physical cause, validate analyst-authored source relationships, rank hypotheses, or produce confidence scores.
- It does not run new threshold, baseline, mask, or evidence-subset sensitivity calculations. It only links already retained variants and states when none are linked.
- It does not turn contextual reporting or optical products into validation of a specific SAR-derived boundary.
- It does not select or retrieve new observations. Follow-up recommendations are existing, recorded investigation plans, not an AI-ranked acquisition plan.
- It does not generate a new map overlay for the challenge. The dossier links to the existing measurement and source-inspection interface.
- A reproducible summary is not equivalent to a scientifically accepted result; provider QA and case disposition remain controlling.

## Verification

Automated coverage exercises T163 source-linked reproducibility, summary-tampering rejection, invalid acquisition-pair identities, missing/unassessed evidence, acquisition-review checksum failure, case-wide scope labeling, Iraq provider-QA gating and preview/QA mismatch rejection, API behavior, and progressive rendering. The focused challenge/API/renderer suite passed **15 tests**; the full suite passed **455 tests**. `compileall` and `git diff --check` passed. The existing Firefox walkthrough exercised the T163 challenge, opened its linked sensitivity source in the source inspector, and confirmed the separate human-review-note action; the Iraq challenge displayed the provider failures and no change conclusion. Browser interaction with the newly grouped comparability panel has not yet been rechecked in this implementation step.

Full-suite and current browser verification results are recorded in the implementation handoff after the final run.
