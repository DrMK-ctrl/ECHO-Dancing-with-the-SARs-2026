# Source-linked investigation draft workflow

**Result:** Pair-analysis records can enter a browser-driven, unassessed investigation plan with one falsifiable, hypothesis-specific next observation.

## Exercised behavior

- The GCOV and OPERA pair inspectors offer **Start investigation draft**.
- The analyst enters a question, two competing hypotheses, each hypothesis's scope, expected observation, weakening condition, and evidence need.
- The analyst selects one hypothesis for a proposed next observation and records the search action, discriminating question, expected and weakening observations, inconclusive condition, acceptance gates, interpretation limit, possible interpretation, and reason for prioritizing the test.
- ECHO creates a source-linked record with canonical JSON SHA-256, retains the submitted pair record, and renders the hypotheses and planned workstream through the shared investigation renderer.
- The source status remains visible in the record. Each hypothesis remains `NOT_EVALUATED`; its evidence references and assessments remain empty. The proposed follow-up remains `NOT_SEARCHED` with one test target.
- The record can be inspected and downloaded as JSON. It is not persisted by the local server.

## Verification

From the repository root:

```bash
.venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q
.venv/bin/python -m pytest -q
git diff --check
```

Results at this checkpoint: focused tests **38 passed**; full suite **310 passed**; `git diff --check` passed.

A headless Firefox session loaded the local ECHO interface, opened the draft dialog using a controlled `QA_HELD` GCOV pair fixture, completed two hypotheses and a next-observation design, and submitted it through the local API. The rendered output showed `DRAFT_NOT_ASSESSED`, the user-selected target hypothesis, and a `NOT_SEARCHED` follow-up. This validates interface and contract integration only. The fixture is not an observation, no satellite retrieval occurred during the browser check, and no scientific hypothesis was evaluated.

## Limits and next validation

The pair record is accepted as submitted and checksummed; provider re-fetch, persisted draft storage, source retrieval for planned observations, and scientific-suitability assessment are not implemented here. The analyst-authored relationships and test design are structurally validated, not scientifically endorsed. The QA-held NISAR route remains a planning workflow and does not create a measurement. The OPERA route remains diagnostically classified. The next substantive step is a source-aware path for attaching retrieved follow-up evidence, validating its provenance and suitability, and then recording explicit analyst-reviewed evidence relationships without treating provider credibility as proof of an interpretation.

See [Decision 0058](../decisions/0058-start-source-linked-investigations-from-pair-records.md).

## Subsequent implementation status — 2026-11-08

The limits above describe the original draft-workflow checkpoint. Later work added private immutable draft snapshots and restart-safe restore; explicit revision rounds linked by parent checksums; source staging and analyst gate screening; import of checksum-verified evidence from the active case; and follow-up NISAR GCOV catalog and provider-QA retrieval records. The catalog and QA attachments remain metadata-only and cannot satisfy a scientific evidence gate. Screening and source relationships remain analyst-authored, unauthenticated, and unverified. In particular, no NISAR measurement pair has been promoted through this workflow.

The shared investigation contract now also rejects directional relationships for explicit QA-held, maturity-held, diagnostic-SAR, catalog-only, and provider-QA-only evidence. Counterfactual previews enforce the same boundary. Current verification is **371 software tests passed**, Python compilation passed, and `git diff --check` passed. See [private draft persistence](local-investigation-draft-persistence-2026-11-08.md), [case evidence import](investigation-case-evidence-import-2026-11-08.md), [follow-up catalog screen](followup-gcov-catalog-screen-2026-11-08.md), [provider-QA link](followup-provider-qa-link-2026-11-08.md), and [non-directional evidence validation](non-directional-evidence-guard-2026-11-08.md).

Remaining boundary: source retrieval is implemented for bounded NISAR catalog metadata and provider QA, while pixel retrieval and QA-gated analysis still depend on compatible products. Case-source import verifies retained record integrity and links, not provider authenticity or scientific fitness. The workflow remains a case-oriented, human-reviewed investigation aid, not a scientifically autonomous or fully generalized Investigation Engine.
