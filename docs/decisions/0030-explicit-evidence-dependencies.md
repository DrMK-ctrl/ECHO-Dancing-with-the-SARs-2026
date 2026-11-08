# Decision 0030: Record evidence derivation and shared observations

**Date:** 2026-11-08
**Status:** Implemented in the T163 diagnostic investigation record

## Context

Evidence relationships identify whether a record supports, contradicts, or limits a hypothesis. They do not by themselves show whether two records are independent. In the current case, spatial overlays are calculated from SAR and optical records, while VV and VH measurements share acquisition dates and processing. Treating each result as a separate corroborating source could overstate the evidence.

## Decision

- Each linked evidence artifact carries `lineage.derived_from_evidence_ids` for inputs used to calculate that record.
- `lineage.shares_source_observations_with` records common source acquisitions when one evidence product is not derived from the other.
- Validate references against the assessment's artifact identifiers and reject self-links, duplicates, missing records, and derivation cycles.
- Expose the graph in a collapsed source-inspection section. Preserve the existing human-authored evidence relationships and deterministic hypothesis dispositions; lineage does not calculate evidence weight, independence probability, or confidence.

For T163, native-grid spatial support records identify their SAR and optical inputs. The VH pair links to the VV pair as sharing source acquisitions. The VV/VH sensitivity result links to both measurements and their spatial-support analyses. GPM remains a separate NASA precipitation context record.

## Limits

This graph records known computational and acquisition dependencies. It does not establish full statistical independence, validate source science, clear provider QA, or infer causation. Missing lineage must not be interpreted as proof that records are independent.

## Verification

The implementation rejects invalid lineage references and cycles. The regenerated assessment retains nine checksum-linked evidence records and keeps its physical-cause disposition unresolved.
