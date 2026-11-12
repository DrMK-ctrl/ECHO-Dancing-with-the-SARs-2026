# Clean-environment curated demo check — 2026-11-12

## Result

The documented local curated demo starts from an isolated virtual environment created with the pinned `requirements.lock`. The read-only server exposed one retained case at a time, rendered the expected quality state in Firefox, and rejected provider and mutation POSTs server-side.

This is a same-machine isolated-environment check, not acceptance on a separate Ubuntu account or a packaged distribution. The source checkout remains required because the lock installs ECHO in editable mode.

## Environment and launch

- Host Python: 3.14.4.
- Environment: fresh `/tmp` virtual environment.
- Dependencies: `python -m pip install -r requirements.lock` inside that environment; lock SHA-256 `b91327184b074d91c12f392e1e8bb7116b710bb71b1906eaff8107fe06f2835c`.
- No Earthdata credentials were needed for the retained case views.
- ECHO was launched with the documented `serve --read-only-demo --case-file ...` command on loopback using non-default test ports.

## Runtime checks

- Iraq case: HTTP 200 for `/`, `/api/cases`, `/api/case`, `/api/review`, and `/api/qa-reports`; the registry listed one case and marked `provider_actions_enabled=false`. Headless Firefox displayed the curated-mode banner, one disabled case option, the QA-held state, and the map SVG.
- Iraq write boundary: POST requests to `/api/catalog`, `/api/gcov-preview`, and `/api/investigation-drafts` each returned HTTP 403 `READ_ONLY_DEMO`.
- T163 case: headless Firefox opened the case investigation, selected the recorded H2 water-change explanation, and expanded the challenge sensitivity section. The rendered panel showed the retained VV and VH summaries, the 50–95% optical support variants, the unresolved QA wording, source-inspection buttons, and the explicit no-stability-score limitation.
- The existing full test suite passed 460 tests; Python compilation and `git diff --check` passed at the implementation checkpoint.

## Limits

- The test environment and HTTP servers ran on the same development host; this does not prove installation in a clean OS account, portability to another Ubuntu release, offline operation, or distribution rights for a data bundle.
- Read-only demo mode is loopback-only and has no remote user authentication. It is not an internet-accessible judge build.
- The T163 analysis remains diagnostic. Rendering its recorded results does not clear OPERA QA or validate a causal explanation.
- No temporal result was added or promoted for the Iraq QA-held NISAR products.
