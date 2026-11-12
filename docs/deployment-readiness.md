# ECHO local and judge-access readiness

**Reviewed:** 2026-11-12
**Status:** Local development launch is available. A secure, independently hosted judge build is not implemented or deployed.

## What can be run now

From the repository root on Ubuntu, with the project environment installed:

```bash
.venv/bin/echo serve --case-file data/cases/iraq-2026-nisar-diagnostic/catalog.json
```

Open `http://127.0.0.1:8765/`; stop the server with Ctrl+C. The default bind is loopback. Other retained cases can be opened by changing `--case-file`, for example the Mozambique pilot or the Rio Grande do Sul T163 diagnostic case. The `README.md` contains the current case walkthroughs and scientific boundaries.

The base Python environment is pinned in `requirements.lock`; Python 3.11 or newer is required. Authenticated NISAR/OPERA data reads and QA retrieval use the optional dependencies pinned in `requirements-nisar.lock` and Earthdata Login configuration in the user's local `~/.netrc`. Keep credentials out of case bundles, logs, screenshots, and this repository. The app does not need Earthdata credentials for retained case records or catalog metadata search. Some map layers and live requests require an internet connection; the interface has map-grid fallback behavior, but the whole application has not been verified as an offline package.

## Read-only and exposure boundary

The default server bind is local, but the application is **not a read-only service**. It has POST operations for catalog searches, on-demand QA and raster retrieval, case-specific analysis, and local investigation-draft creation/revision. It does not currently have a deployment-grade user authentication layer or a curated read-only demo mode. The Bhoonidhi credential route enforces a loopback, same-origin request check; that route-specific protection does not secure the application as a whole. The CLI accepts a non-loopback `--host`, which must not be used to make the current service reachable by judges or a LAN.

Do not port-forward, reverse-proxy, or bind the current app to a public or shared network. A read-only filesystem alone would not make the service safe: write-capable routes and live provider requests need an explicit application-level policy, and a proxy would need to authenticate users and constrain requests.

## Recommended judge-access sequence

1. **Near-term, user-operated demonstration:** run ECHO on the project lead's Ubuntu laptop using the loopback command above. Preselect a retained case, rehearse its actual data and QA state, and keep Earthdata credentials local. Clearly disclose which actions need network access and which cases are diagnostic or QA-held.
2. **Prepare a curated read-only build:** define a case bundle containing only reviewed records, required static assets, their licenses/attributions, checksums, and a manifest. Add an application-level read-only mode that rejects every write or external-retrieval route by default, serves only the included allowlisted evidence, and displays a clear offline/curated-data status. Add automated route-level tests proving mutation and provider access are denied in this mode. Do not rely on filesystem permissions as the only control.
3. **Only if independent remote access is needed and later authorized:** deploy an isolated copy of that curated mode behind TLS and access control, with no Earthdata or Bhoonidhi secrets, no writable source/data mount, bounded request resources, and logs that exclude credentials. Review data and asset redistribution rights before packaging. Validate the exact URL, account flow, network policy, backup, rollback, and shutdown procedure before any external access.

The current code is at step 1. Steps 2 and 3 are recommendations, not completed features. No public endpoint, remote judge account, release, or deployment has been created.

## Verification checklist before a judge build

- [ ] Confirm competition eligibility, team registration, submission terms, and the exact local Beirut presentation requirements from organizer sources; do not treat private repository access as submission permission.
- [ ] Select one scientifically meaningful case whose actual data, quality disposition, and limitations are explicit. Keep Iraq NISAR QA-held and OPERA T163 diagnostic unless their evidence gates change.
- [ ] Reproduce the case from a clean Ubuntu account using documented pinned dependencies; verify startup, shutdown, expected map state, acquisition timeline, source inspector, and failure messages.
- [ ] Test supported actions in browser and API, including QA-held products, missing network, provider errors, invalid/oversized requests, and resource limits.
- [ ] For read-only mode, enumerate every HTTP route and prove by tests that all writes, revision/import actions, and provider retrieval endpoints are disabled; ensure only checksum-verified bundle paths can be read.
- [ ] Inspect package contents for credentials, local user data, unreviewed artifacts, licenses, attribution, and unintended source/history exposure.
- [ ] Verify map/layer provenance, acquisition timestamps, processing records, QA disposition, and distinction between measured values, derived values, hypotheses, and unresolved findings.
- [ ] Record the exact build revision, dependency lock hashes, case-bundle hash, browser/OS versions, and verification results.
- [ ] Obtain explicit project-lead approval for any external deployment, account sharing, release, or publication. None is authorized by this readiness note.

## Current readiness assessment

ECHO is suitable for a guided local technical walkthrough, not yet for unattended judge access. The map, retained evidence, live catalog search, bounded measurement preview, QA-first comparison path, and case-specific investigation flow are connected in the local interface. Current scientific evidence does not include a QA-cleared NISAR temporal change result. The QA-held Iraq and Nepal scenes can demonstrate source inspection and gate behavior; the OPERA case can demonstrate a diagnostic, multi-source investigation, but neither should be presented as a validated causal finding. See [`PROJECT_CHARTER.md`](PROJECT_CHARTER.md), [`2026-11-11-p05036-gcov-qa-root-cause.md`](research/2026-11-11-p05036-gcov-qa-root-cause.md), and [`2026-11-11-incremental-nisar-gcov-screen.md`](research/2026-11-11-incremental-nisar-gcov-screen.md).
