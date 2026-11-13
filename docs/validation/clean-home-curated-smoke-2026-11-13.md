# Curated ECHO startup with isolated user state

**Run:** 2026-11-13 09:06 UTC  
**Code revision:** `d649604`  
**Mode:** source-tree `.venv` CLI, `--read-only-demo`, loopback only

## Result

ECHO started on an ephemeral loopback port with a temporary `HOME` and
`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, and `XDG_CACHE_HOME`. The selected case was
the retained Rio Grande do Sul T163 investigation, loaded from the checkout's
curated case data root.

- `GET /api/cases`: HTTP 200; `CURATED_READ_ONLY`, one case,
  `provider_actions_enabled=false`.
- `GET /api/review`: HTTP 200; review status `DIAGNOSTIC_CASE`.
- `GET /api/investigation-drafts`: HTTP 403, as required in read-only mode.
- The temporary home contained no Earthdata `.netrc`; no Earthdata token was
  configured for the check. No provider request was made.
- The temporary server exited after the check; no project files or user draft
  state were written.

## Scope limit

This verifies curated-mode startup and API behavior with isolated user
configuration on the development host. It still uses the checkout's `.venv`,
source code, and evidence root. It does not verify a wheel-installed build, a
separate Ubuntu account, GNOME app-grid activation, or redistribution of the
case bundle.
