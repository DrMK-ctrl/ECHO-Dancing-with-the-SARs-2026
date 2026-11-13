# Installed-wheel smoke test with isolated user state — 2026-11-13

## Scope

This check exercised a newly built ECHO wheel outside the source checkout, with
a separate retained-case bundle and a temporary `HOME`. The isolated home had
no `.netrc`; ECHO did not need Earthdata credentials to serve retained evidence.
The test ran on the development host, so it is not a separate-account or
separate-machine acceptance test.

## Build and environment

- Wheel: `echo_sar_investigation-0.1.0-py3-none-any.whl`
- Wheel SHA-256: `64e47a3c6074726c5267f0bacb550005e60bfb02eeb5614fa555a6671dbefd7f`
- Built locally from the ECHO worktree and installed into the isolated
  `/tmp/echo-eval-venv` without installing the source checkout.
- Data root: `/tmp/echo-curated-bundle`, containing the retained Iraq case and
  linked review evidence; the bundle has no Earthdata credentials.
- Server: `127.0.0.1:8787`, started with `--read-only-demo`; stopped after the
  check. The user's existing workbench and demo services were not changed.

## Results

- With `HOME=/tmp/echo-isolated-home-nov13` and no `.netrc`, the application,
  case registry, case catalog, review, and QA-report endpoints returned HTTP
  200. A catalog POST returned HTTP 403 `READ_ONLY_DEMO`.
- Firefox 158.0.1 opened the installed-wheel application. The one-case
  selector was disabled, the curated read-only banner was visible, the map SVG
  rendered at 788 CSS pixels, and the Iraq provider-QA `FAIL` and
  diagnostic-only disposition remained visible. The provider-search control
  was disabled.
- No provider request was made. The retained observation remains
  `QA_HELD_DIAGNOSTIC_PREVIEW`; the check does not calculate change or establish
  a physical interpretation.

This strengthens the same-host installed-package check: the serving wheel came
from the current local code, data was separate from the checkout, and execution
did not depend on the developer's Earthdata configuration. It does not establish
operation on another Ubuntu account or release, offline behavior, distribution
rights for the bundle, or suitability for external judge access.
