# Provider QA linkage to investigation follow-up — 2026-11-08

## Scope

Validated the application path that resolves one returned NISAR GCOV scene from the retained catalog response, retrieves its canonical ASF provider-QA CSV through ECHO's existing bounded reader, and links the resulting record to an open, pre-registered investigation follow-up. Automated endpoint and Firefox tests use deterministic QA fixtures; a separate local API invocation performed one live ASF QA retrieval. No radar-array retrieval or scientific compatibility determination was performed.

## Checks

- Draft validation requires the provider QA record's scene ID and feature to match a scene in the retained parent catalog result, and preserves the parent response checksum and follow-up test-design link.
- An ID absent from the retained catalog result is rejected before the QA reader is called.
- The attachment endpoint accepts only the draft, parent catalog evidence ID, and selected scene ID; it retrieves the QA response itself and does not accept a browser-submitted QA payload. The QA record retains retrieval details, source URI, response checksum, and the parsed ASF disposition.
- For a retrieval marked as performed by ECHO at attachment, record validation requires network-retrieval metadata, the Earthdata/netrc method, a positive range-read count, matching response/evidence checksums and URIs, a timezone-aware retrieval timestamp, and the canonical ASF host and per-scene QA path.
- A provider QA `FAIL` remains present in the attached record. The role is non-directional and is rejected both as hypothesis support/contradiction and as a follow-up gate-screening source.
- API and UI linkage tests verify that staging does not alter hypothesis relationships or follow-up screening state.
- The source inspector identifies QA metadata as metadata-only and states that test fit, independence, spatial/temporal suitability, and radar-array interpretation are not established. The application distinguishes an ECHO retrieval at attachment from an unverified supplied snapshot.
- The focused regression run `tests/test_investigation_draft.py tests/test_web.py` passed: **57 passed**.
- The Firefox walkthrough uses deterministic local catalog and provider-QA fixtures. It exercises the linked selection, QA inspection, attachment, and source inspector; it is UI integration evidence only, not a live NASA/ASF test.

## Live provider retrieval

At `2026-11-08T18:53:43Z`, a temporary local HTTP server exercised the new attachment endpoint with an actual feature from the retained ASF VALIDATED GCOV screen. The endpoint resolved scene `NISAR_L2_PR_GCOV_034_120_D_072_2005_DHDH_M_20261101T124845_20261101T124920_P05036_N_F_J_001`, fetched its canonical QA CSV through Earthdata Login and the bounded ASF reader, and returned HTTP `200`. The CSV was 1,441 bytes with SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`; the provider disposition remained `FAIL`. The response recorded Earthdata/netrc authentication, HTTPS byte-range streaming, 1,441 requested range bytes, and `network_retrieval: true`. The draft's hypothesis states, evidence relationships, and follow-up state remained unchanged; no radar arrays were read and no draft was saved.

## Result and limits

The user can carry the provider's current QA disposition for a specific catalog candidate into its motivating follow-up without converting QA into a scientific finding or weakening the existing gates. Both the live endpoint check and deterministic tests preserve a QA `FAIL`. The live check verifies retrieval integration for this one scene; it does not establish product-level QA suitability for this test, observation compatibility, or broader service availability. No validated NISAR temporal comparison or change result is claimed.
