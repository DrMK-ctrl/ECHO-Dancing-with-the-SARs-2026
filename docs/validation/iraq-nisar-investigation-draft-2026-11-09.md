# Iraq NISAR observation to investigation draft — 2026-11-09

## Result

The selectable `iraq-2026-nisar-gcov-diagnostic` case now exercises the map-to-investigation workflow using the retained real October 20 NISAR GCOV HHHH preview. The interface created an `UNASSESSED DRAFT` with the exact source record and checksum. ECHO retained the source role `DESCRIPTIVE_NISAR_SINGLE_OBSERVATION`, the status `QA_HELD_DIAGNOSTIC_PREVIEW`, two `NOT EVALUATED` hypotheses, and one `NOT SEARCHED` follow-up.

The test question was whether a future QA-cleared, compatible repeat would show a reproducible temporal difference in the AOI's HHHH backscatter pattern. The alternatives described stable versus changing patterns on comparable valid pixels. The proposed repeat was gated on provider QA, product and geometry compatibility, verified grid alignment, common valid support, and a documented uncertainty criterion. The draft explicitly says a repeatable radar-response difference would not establish flood extent, damage, or physical cause.

## Runtime path and artifact

Headless Firefox opened the registered Iraq case, selected the October 20 timeline observation, loaded the retained authentic preview record through the map flow, opened **START INVESTIGATION**, and submitted the test draft through the application's draft API. The screenshot shows the generated draft and its one-source/two-hypothesis matrix: [`iraq-nisar-investigation-draft-2026-11-09.png`](assets/iraq-nisar-investigation-draft-2026-11-09.png), SHA-256 `b86ee4d037c769f57b6beac254292aa38f320a29e0d113ee3a564ac635e4e487`.

The browser supplied the already-retained preview JSON as a local fixture only for the `/api/gcov-preview` request, avoiding a duplicate multi-megabyte ASF range retrieval. The case registry, map selection, preview renderer, investigation form, and draft-creation API ran through the local application. A separate live browser check had already retrieved and rendered the real preview from ASF; its request and source bytes are documented in the [workspace validation](iraq-nisar-case-workspace-2026-11-09.md).

The question, hypothesis text, and follow-up in this browser exercise were test inputs authored for validation. The draft was not saved as a case assessment or exported record. No evidence relationships were assigned, no hypothesis was evaluated, and no scientific conclusion was generated.

## Case-source import integration

The Iraq case now exposes a small `ECHO_CASE_SOURCE_MANIFEST` for its catalog screen and provider-QA screen. The draft import API verifies the selected case, exact preview scene, source paths within the project root, SHA-256 values, record types, and scene links before embedding either JSON record. The imported source artifacts explicitly share the primary SAR observation, remain `NOT_ASSESSED` for independence, and retain the provider QA `FAIL` rows. Their roles are metadata-only and non-directional.

The end-to-end API test created an unassessed draft from the retained October 20 preview, listed the two case sources, imported both, checked their shared-observation lineage, and confirmed the QA failures remained unchanged. It also altered a manifest checksum and confirmed the API rejected that source with HTTP 409. The existing assessment-backed OPERA case import still passes its separate compatibility test. The complete test suite passed: **434 passed**.

This is record-integrity validation against the local case manifest, not cryptographic provider authentication, independent corroboration, source fitness assessment, or a validated finding. The analyst draft remains unassessed and no measurement or conclusion is added by this import.

## Verification boundary

This confirms that the newly registered real-data case can enter ECHO's existing analyst-guided investigation workflow. It does not validate the provider-QA-failed products, establish a temporal change, show that the proposed follow-up is available, or validate a physical explanation. The actual October 8–20 metadata pair remains held because both products report provider QA `FAIL`.
