# Provider QA linkage to investigation follow-up — 2026-11-08

## Scope

Validated the application path that links an ASF provider-QA inspection snapshot for one returned NISAR GCOV scene to an open, pre-registered investigation follow-up. No live ASF request, radar-array retrieval, or scientific compatibility determination was performed for this change.

## Checks

- Draft validation requires the provider QA record's scene ID and feature to match a scene in the retained parent catalog result, and preserves the parent response checksum and follow-up test-design link.
- The inspection snapshot is checksummed and retained with an explicit state that retrieval provenance was not reverified during attachment.
- A provider QA `FAIL` remains present in the attached record. The role is non-directional and is rejected both as hypothesis support/contradiction and as a follow-up gate-screening source.
- API and UI linkage tests verify that staging does not alter hypothesis relationships or follow-up screening state.
- The source inspector identifies QA metadata as metadata-only and states that test fit, independence, spatial/temporal suitability, and radar-array interpretation are not established.
- The focused regression run `tests/test_investigation_draft.py tests/test_web.py` passed: **57 passed**.
- The Firefox walkthrough uses deterministic local catalog and provider-QA fixtures. It exercises the linked selection, QA inspection, attachment, and source inspector; it is UI integration evidence only, not a live NASA/ASF test.

## Result and limits

The user can carry a specific provider QA snapshot from a retained catalog candidate into its motivating follow-up without converting QA into a scientific finding or weakening the existing gates. The attachment records the supplied inspection and its checksum but does not authenticate its provider origin, repeat retrieval, assess product-level QA suitability for this test, or establish that an observation is compatible. No validated NISAR temporal comparison or change result is claimed.
