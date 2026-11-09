# Guaíba primary gauge-series access gate

Date: 2026-11-09

## Result

ECHO now distinguishes a source that requires authorization from one that has not been searched or has no suitable data. The T163 investigation records an `ACCESS_REQUIRED` follow-up for the original-reference Usina do Gasômetro emergency station series (`87444000`). The follow-up appears under **OPEN EVIDENCE SEARCH** and links a source record documenting the access state.

The official ANA/SGB station note says readings from 2024-05-03 through 2025-08-29 are retained under station `87444000`. ANA's current [HidroWebService manual](https://www.gov.br/ana/pt-br/assuntos/monitoramento-e-eventos-criticos/monitoramento-hidrologico/orientacoes-manuais/manuais/manual-hidrowebservice_publica.pdf/%40%40download/file) requires an access request to `hidro@ana.gov.br`, including the applicant's CPF or CNPJ, name, and email; credentials are issued if the request is approved. The legacy query and current inventory miss do not establish that the archive is absent.

No access request was sent, no personal identifier or credentials were collected, and no gauge values are represented as retrieved. The series screen retains the official source references and exact requested SAR timestamps. It keeps emergency station `87444000` separate from corrected station `87450020` and forbids unjustified interpolation.

## Scientific boundary

If retrieved, the point-gauge series could refine nearby stage chronology at the two SAR dates. It cannot establish water extent inside the SAR AOI or validate SAR-derived change. The T163 hypotheses remain `UNRESOLVED`; the RTC-S1 pair remains diagnostic. No measurement, evidence relationship, or conclusion was promoted by adding the access state.

## Verification

- Builder validation binds the access record to the exact T163 case, station identity, two SAR acquisition timestamps, official API and station-archive references, and `series_retrieved: false`.
- An assessment rebuild preserves the prior six hypotheses and unresolved causal disposition, retains the previous 23 evidence artifacts and adds the access metadata artifact (24 total), and adds one open follow-up (11 total).
- The retained case-evidence import route carries the access record into an unassessed draft with its access-only role and `series_retrieved: false` intact. The draft UI displays an explicit access-only notice and excludes the source from its screening selector. The analyst follow-up screening endpoint rejects that record with HTTP 422 and states it is not a retrieved observation, even when every acceptance gate is submitted as met. The assessment endpoint also rejects a `SUPPORTS` claim from that access-only metadata with HTTP 422.
- Focused checks: `PYTHONPATH=. .venv/bin/pytest tests/test_investigation.py tests/test_cross_sensor_investigation.py -q --tb=short` — **83 passed**.
- Case-import, observation-screen, and directional-claim regression: `.venv/bin/python -m pytest -q tests/test_web.py::test_investigation_draft_imports_only_validated_case_sources_for_exact_sar_pair` — **1 passed**.
- A local API plus headless Firefox check loaded a source-linked T163 draft and imported the retained Guaíba access record. The rendered draft showed the access-only notice; `SCREEN NEXT-OBSERVATION SOURCE` remained disabled; and the access record was absent from the screening-source picker.
- Full suite after this refinement: `.venv/bin/python -m pytest -q` — **387 passed**.
- Python compilation, `git diff --check`, and GJS JavaScript parsing passed. The shared investigation renderer was evaluated against the rebuilt T163 record in GJS; assertions confirmed that the access-required step appears under the open evidence-search section with its action text.
- The current full T163 rebuild command, exact record comparison, and 24-artifact source validation are documented in the [end-to-end workflow record](end-to-end-investigation-workflow-2026-11-08.md#current-assessment-rebuild--2026-11-09).

Sources: [ANA HidroWebService manual](https://www.gov.br/ana/pt-br/assuntos/monitoramento-e-eventos-criticos/monitoramento-hidrologico/orientacoes-manuais/manuais/manual-hidrowebservice_publica.pdf/%40%40download/file); [ANA/SGB station reconfiguration note](https://rigeo.sgb.gov.br/bitstream/doc/24911/4/nota_institucional_conjunta_ana_sgb_gasometro.pdf); [ANA 2025 hydrologic chronology](https://conjuntura2025.ana.gov.br/agua-e-clima.html).
