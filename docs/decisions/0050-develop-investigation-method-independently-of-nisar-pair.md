# Develop the investigation method independently of a cleared NISAR pair

**Date:** 2026-11-08
**Status:** Initial reusable contract implemented; end-to-end workflow evaluation remains open

## Context

ECHO has a real, case-scoped diagnostic OPERA RTC-S1 investigation with retained measurements, source-linked competing hypotheses, relationships for supporting, contradictory, non-distinguishing, and limiting evidence, falsifiable follow-up designs, evidence lineage, and explicit QA and interpretation boundaries. Deterministic validation primitives also have synthetic unit coverage. The assessment is not a generalized investigation workflow, and the method has not been evaluated as a coherent end-to-end capability.

The unresolved NISAR temporal-pair gate prevents a validated NISAR change finding. It does not prevent exercising whether ECHO preserves provenance, distinguishes evidence roles, handles conflict and missing evidence conservatively, and specifies a testable next question. Requiring a cleared NISAR pair before those workflow capabilities can progress would couple independent engineering work to a data-availability condition.

## Decision

Advance a reusable, deterministic investigation workflow as a workstream independent of the NISAR temporal-pair gate. Use the retained T163 diagnostic investigation to exercise the real evidence path and controlled synthetic reasoning scenarios to check defined workflow behaviors. Preserve each evidence source's actual QA and status. Never present a synthetic case as an observation or scientific result, and never promote the diagnostic OPERA case to a validated causal finding.

The initial evaluation should be limited to observable workflow properties:

- every hypothesis assessment resolves to registered, inspectable evidence;
- contradictory, non-distinguishing, or interpretation-limiting evidence does not produce a directional disposition;
- missing or unsearched evidence remains an explicit gap;
- shared source observations are not described as independent corroboration;
- each proposed discriminating follow-up identifies one hypothesis, expected and weakening observations, inconclusive conditions, and acceptance gates; and
- quality prerequisites remain distinguishable from scientific evidence searches.

These checks evaluate workflow behavior, not scientific accuracy, causal validity, or the value of the investigation. Retain explicit priority rationale and feasibility. Do not add a numeric information-gain or "best next observation" score until a defensible utility measure and suitable evaluation evidence exist.

## Consequences

- A cleared NISAR pair is still required before claiming a validated NISAR temporal change result.
- A diagnostic real-data investigation can be used to develop the integrated evidence workflow without validating its measurements or causal conclusions.
- Synthetic scenarios can challenge deterministic reasoning and state handling but cannot validate remote-sensing algorithms, source quality, or physical interpretations.
- The next implementation milestone is to make the reusable workflow explicit and independently inspectable across cases, then evaluate it against the properties above before adding AI-assisted reasoning.

## Implementation and verification

`echo.investigation.validate_investigation_contract` now composes evidence-lineage, hypothesis, and follow-up validation without depending on a specific mission or product. The assessment route calls this shared contract after its existing source-artifact and checksum validation. Synthetic contract scenarios verify an explicitly unresolved case and reject a directional disposition that conflicts with non-distinguishing evidence.

- Focused investigation, case-record, and web validation: **77 passed**.
- Full software suite: **297 passed**.
- Python compilation and `git diff --check`: passed.

The contract validates structure and deterministic consistency only. It does not assess scientific suitability, provider QA, source credibility, or whether an analyst-authored evidence relationship is scientifically correct. The T163 real-data workflow remains case-scoped and diagnostic; the NISAR temporal pair and generalized end-to-end workflow remain open.
