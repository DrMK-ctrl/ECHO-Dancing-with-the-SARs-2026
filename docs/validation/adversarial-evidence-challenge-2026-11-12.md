# Adversarial evidence challenge: scoped implementation

**State:** Implemented review workflow; not an autonomous causal evaluator.

## What the challenge does

`Challenge this finding` assembles a deterministic, read-only review from the active case assessment and its linked evidence. The API validates the assessment and its source records before returning the dossier. It keeps the observation, the selected hypothesis, analyst-recorded evidence relationships, competing explanations, linked sensitivity variants, unassessed evidence, and pre-recorded follow-up observations distinct. For T163, it also exposes the checksum-linked acquisition-condition review in a separate case-wide comparability lane when the selected hypothesis did not cite that review. The view labels that scope and does not convert it into directional evidence. It recomputes the displayed VV/VH polarization and DSWx optical-support threshold summaries from checksum-validated per-cell records, then exposes source-inspector links to the records and checksums.

For a linked RTC-S1 pair, the challenge additionally verifies the pair-record checksum and identity, acquisition metadata and support counts. It recomputes the mean and median from the retained `values_db` array under the recorded valid and common-clear masks. It rejects a summary that does not reproduce. This checks arithmetic and record linkage; it does not establish product QA or validate an explanation.

Sensitivity summary recomputation likewise checks the statistics shown against their per-cell inputs; it does not rerun the original RTC-S1 raster calculation or the native-grid DSWx-HLS overlay. See the [sensitivity reproduction validation](adversarial-sensitivity-reproduction-2026-11-12.md) for formulas, observed T163 values, and limits.

## Existing-case behavior

- **T163 Rio Grande do Sul:** The selected water-change explanation remains `UNRESOLVED`; the RTC-S1 pair retains unresolved provider QA. The UI shows the actual acquisition interval and response summary, reports the reproduced measurement check, links the recorded OPERA polarization sensitivity source and other existing evidence, and exposes competing explanations and follow-up plans. It displays retained VV/VH summaries (738 common cells; VV mean/median −2.047/−1.215 dB; VH −1.716/−1.144 dB) and optical WTR support variants (826 SAR cells at 50% support and 738 at 75%, 90%, and 95%). The latter are descriptive optical-support comparisons, not validation. Evidence relationships are labeled as analyst assessments. No aggregate stability verdict is calculated. This remains a diagnostic investigation, not a validated flood finding.
- **Acquisition comparability:** The challenge verifies the review record checksum and reproduces it against the linked pair metadata before returning it. The progressive UI groups this descriptive metadata comparison beside (but separately from) already linked sensitivity records. It shows missing incidence-angle and spatially matched RFI evidence, and explicitly states that matching metadata do not establish raster alignment or clear provider QA. When the review is not cited by the selected hypothesis, it is labeled case-wide and not linked to that hypothesis.
- **Iraq NISAR GCOV:** The case has one QA-held diagnostic preview and a candidate pair whose two products have provider QA `FAIL`. The challenge explicitly says there is no change finding to challenge, exposes the single-observation and QA records, and returns no change conclusion. It does not calculate temporal change or infer an event.

## What it does not claim or calculate

- It does not infer a physical cause, validate analyst-authored source relationships, rank hypotheses, or produce confidence scores.
- It does not run new threshold, baseline, mask, or evidence-subset processing. It reproduces selected retained per-cell sensitivity summaries; other linked records remain source-linked only.
- It does not turn contextual reporting or optical products into validation of a specific SAR-derived boundary.
- It does not select or retrieve new observations. Follow-up recommendations are existing, recorded investigation plans, not an AI-ranked acquisition plan.
- It does not generate a new map overlay for the challenge. The dossier links to the existing measurement and source-inspection interface.
- A reproducible summary is not equivalent to a scientifically accepted result; provider QA and case disposition remain controlling.

## Verification

Automated coverage exercises T163 source-linked reproducibility, recomputation and tamper rejection for sensitivity summaries, invalid acquisition-pair identities, missing/unassessed evidence, acquisition-review checksum failure, case-wide scope labeling, Iraq provider-QA gating and preview/QA mismatch rejection, API behavior, and progressive rendering. The focused adversarial suite passed **15 tests** and the full suite passed **463 tests**. `git diff --check` passed. The JavaScript renderer test executed in the full suite and confirms the recomputation basis is visible; a new interactive Firefox walkthrough was not performed for this change.

A follow-up headless Firefox walkthrough verified the newly grouped panel through the visible workflow: open the T163 assessment, challenge the H2 water-change explanation, expand the initially collapsed “Comparability and sensitivity” section, and inspect its linked acquisition-condition record. The browser showed `CASE WIDE NOT LINKED TO SELECTED HYPOTHESIS`, exposed the recorded incidence-angle and provider-QA limits, and opened the source record with its SHA-256 provenance. This confirms interface wiring and disclosure behavior; it does not validate the analyst-authored hypothesis or upgrade the diagnostic SAR pair.

## Summary disclosure refinement — 2026-11-12

The read-only T163 assessment previously opened with its full 1,885-character synthesis before any observation cards. The first view now shows the opening observation sentence, with the complete synthesis under **Read full assessment synthesis**. The two primary observation cards (diagnostic SAR and DSWx-HLS context) remain visible; eight secondary context and quality-check records start collapsed under **More context and quality checks**; and four comparability/sensitivity variants start collapsed under their own disclosure. The acquisition chronology remains visible. Expanding either evidence group retains its existing source-inspection controls.

Headless Firefox verified the collapsed initial state, then expanded both evidence groups and confirmed all eight secondary records, all four sensitivity checks, and a linked GPM source button. The [browser capture](assets/t163-investigation-progressive-summary-2026-11-12.png) shows the initial state. This is a presentation change only; the assessment record, calculations, source relationships, QA state, and interpretation limits are unchanged.
