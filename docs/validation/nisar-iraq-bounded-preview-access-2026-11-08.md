# NISAR Iraq bounded preview access check — 2026-11-08

## Result

An attempt to build a small single-observation HHHH preview from the 2026-10-20 P05023 scene over a `[41.20, 36.70, 41.22, 36.72]` WGS84 window failed during the HDF5 HTTPS range read. The same authenticated session had retrieved the provider QA summary first. No measurement arrays were read and no preview record was written. The scene remains provider-QA `FAIL` on its aggregate identification-group check, so even a successful retrieval would have been diagnostic only.

A separate authenticated 1 KiB HTTP range read from the beginning of the same 1.93 GB product returned `206 Partial Content`. This verifies the account and initial byte-range path; it does not prove that the later HDF5 metadata and measurement ranges are available. The observed error was `aiohttp.ClientOSError` caused by a connection reset during HDF5 dataset lookup. One occurrence does not identify a persistent ASF restriction or a reader defect. No identical full-window retry was made.

The exact scene, request parameters, failure stage, QA linkage, and successful initial-range response are retained in the [structured attempt record](../../data/research/nisar-iraq-p05023-hhhh-preview-access-attempt-2026-11-08.json). The earlier [catalog and QA records](provisional-gcov-coverage-and-qa-2026-11-08.md) remain authoritative for product identity and QA disposition.

## Consequence

This attempt does not change the existing validated NISAR preview path, does not create new measurements, and does not establish a geographic coverage limitation. If this scene is revisited, first distinguish the one-off range reset from repeatable reader behavior; preserve the QA hold and bounded-read limit.
